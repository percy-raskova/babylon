"""Kernel accounting and exact-child suspension; no national game is launched."""

from __future__ import annotations

import base64
import errno
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import replace
from pathlib import Path
from typing import BinaryIO

import pytest
from pydantic import ValidationError
from tools.devtools import national_game_memory as memory


def stat(pid: int = 17, start: int = 123) -> bytes:
    return (
        f"{pid} (unusual ) comm) ".encode()
        + b" ".join([b"S", *([b"0"] * 18), str(start).encode()])
        + b"\n"
    )


def rollup() -> bytes:
    return b"Rss: 12 kB\nPss: 8 kB\nSwap: 2 kB\nPrivate_Hugetlb: 0 kB\nShared_Hugetlb: 4 kB\n"


def fake_proc(tmp_path: Path) -> memory.ProcessBinding:
    process = tmp_path / "17"
    process.mkdir()
    (process / "stat").write_bytes(stat())
    (process / "smaps_rollup").write_bytes(rollup())
    (process / "exe").write_bytes(b"frozen executable preimage")
    boot = tmp_path / "sys/kernel/random"
    boot.mkdir(parents=True)
    (boot / "boot_id").write_text("00000000-0000-0000-0000-000000000001\n")
    return memory.ProcessBinding(
        pid=17,
        start_time_ticks=123,
        role="engine-runtime",
        executable_sha256=hashlib.sha256((process / "exe").read_bytes()).hexdigest(),
    )


def test_kernel_stat_handles_spaces_and_closing_parentheses() -> None:
    assert memory.parse_start_time(stat(), 17) == 123
    with pytest.raises(memory.CaptureRefusal):
        memory.parse_start_time(stat(), 18)


def test_rollup_preserves_kib_swap_and_hugetlb_without_rss_dedup_claim() -> None:
    assert memory.parse_rollup(rollup()) == {
        "rss_bytes": 12 * 1024,
        "pss_bytes": 8 * 1024,
        "swap_bytes": 2 * 1024,
        "private_hugetlb_bytes": 0,
        "shared_hugetlb_bytes": 4 * 1024,
    }


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"Rss: 1 kB\n",
        rollup() + b"Rss: 12 kB\n",
        rollup().replace(b"12 kB", b"12 B"),
        rollup().replace(b"12 kB", b"-12 kB"),
        rollup().replace(b"8 kB", b"13 kB"),
        rollup().replace(b"12 kB", b"999999999999999999 kB"),
    ],
)
def test_missing_malformed_or_overflow_counter_refuses(raw: bytes) -> None:
    with pytest.raises(memory.CaptureRefusal):
        memory.parse_rollup(raw)


def test_sequential_batch_cannot_claim_complete_coherent_snapshot(tmp_path: Path) -> None:
    binding = fake_proc(tmp_path)
    batch = memory.collect_sequential((binding,), tmp_path)
    result = memory.diagnostic_sample(
        batch, 1, memory.AgeMarker(campaign_age_ticks=0, tick_content_hash=None), "not_running"
    )
    assert result.simultaneous_capture == "sequential_unstopped"
    assert result.roster_complete == "incomplete"
    assert result.processes[0].executable_sha256 == binding.executable_sha256
    assert result.processes[0].rss_bytes == 12 * 1024


def test_pid_reuse_refuses_instead_of_using_another_process(tmp_path: Path) -> None:
    binding = fake_proc(tmp_path)
    (tmp_path / "17/stat").write_bytes(stat(start=124))
    with pytest.raises(memory.CaptureRefusal, match="incarnation differs"):
        memory.observe_process(binding, tmp_path)


def test_process_exit_and_wrong_executable_refuse_instead_of_zero(tmp_path: Path) -> None:
    binding = fake_proc(tmp_path)
    (tmp_path / "17/exe").write_bytes(b"replacement executable")
    with pytest.raises(memory.CaptureRefusal, match="provenance differs"):
        memory.observe_process(binding, tmp_path)
    (tmp_path / "17/stat").unlink()
    with pytest.raises(memory.CaptureRefusal, match="disappeared"):
        memory.observe_process(binding, tmp_path)


def test_pid_change_during_smaps_read_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binding = fake_proc(tmp_path)
    original = memory.read_kernel_record
    count = 0

    def changing_stat(path: Path, *, allow_empty: bool = False) -> bytes:
        nonlocal count
        if path.name == "stat":
            count += 1
            return stat(start=123 if count == 1 else 124)
        return original(path, allow_empty=allow_empty)

    monkeypatch.setattr(memory, "read_kernel_record", changing_stat)
    with pytest.raises(memory.CaptureRefusal, match="changed during"):
        memory.observe_process(binding, tmp_path)


@pytest.mark.parametrize("replacement", [False, True])
def test_executable_change_during_hash_refuses_even_with_same_size_and_mtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: bool
) -> None:
    binding = fake_proc(tmp_path)
    executable = tmp_path / "17/exe"
    before = executable.stat()
    original_digest = hashlib.file_digest

    def changed_digest(source: BinaryIO, algorithm: str) -> object:
        result = original_digest(source, algorithm)
        target = tmp_path / "replacement" if replacement else executable
        target.write_bytes(b"x" * before.st_size)
        os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
        if replacement:
            target.replace(executable)
        return result

    monkeypatch.setattr(hashlib, "file_digest", changed_digest)
    with pytest.raises(memory.CaptureRefusal, match="executable changed"):
        memory.observe_process(binding, tmp_path)


def test_empty_parent_cgroup_keeps_all_nested_owned_processes(tmp_path: Path) -> None:
    (tmp_path / "cgroup.procs").write_bytes(b"")
    (tmp_path / "cgroup.type").write_bytes(b"domain\n")
    child = tmp_path / "child"
    child.mkdir()
    (child / "cgroup.procs").write_bytes(b"19\n17\n")
    (child / "cgroup.type").write_bytes(b"domain\n")
    assert memory.cgroup_members(tmp_path) == (17, 19)
    (tmp_path / "cgroup.procs").write_bytes(b"17\n")
    with pytest.raises(memory.CaptureRefusal, match="moved"):
        memory.cgroup_members(tmp_path)


def test_threaded_cgroup_and_false_freeze_barrier_refuse(tmp_path: Path) -> None:
    (tmp_path / "cgroup.procs").write_bytes(b"17\n")
    (tmp_path / "cgroup.type").write_bytes(b"threaded\n")
    with pytest.raises(memory.CaptureRefusal, match="threaded"):
        memory.cgroup_members(tmp_path)
    (tmp_path / "cgroup.events").write_bytes(b"populated 1\nfrozen 0\n")
    with pytest.raises(memory.CaptureRefusal, match="not frozen"):
        memory.verify_cgroup_frozen(tmp_path)
    (tmp_path / "cgroup.events").write_bytes(b"populated 1\nfrozen 1\n")
    memory.verify_cgroup_frozen(tmp_path)


def test_frozen_file_changes_refuse_without_disclosing_contents(tmp_path: Path) -> None:
    expected = {}
    for key, name in memory.CAPTURE_FILES.items():
        (tmp_path / name).write_bytes(b"private synthetic preimage")
        expected[key] = hashlib.sha256(b"private synthetic preimage").hexdigest()
    assert memory.verify_frozen_files(tmp_path, expected) == expected
    (tmp_path / "ownership").write_bytes(b"different private lease")
    with pytest.raises(memory.CaptureRefusal, match="binding changed") as error:
        memory.verify_frozen_files(tmp_path, expected)
    assert "private" not in str(error.value)


@pytest.mark.parametrize("age, digest", [(1, None), (True, "ab" * 32), (0, "ab" * 32)])
def test_age_requires_actual_committed_content_marker(age: object, digest: object) -> None:
    with pytest.raises(ValidationError):
        memory.AgeMarker(campaign_age_ticks=age, tick_content_hash=digest)


@pytest.fixture
def owned_children() -> Iterator[tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]]]:
    """Real disposable children, with a secondary live thread in each child."""
    children = []
    script = (
        "import sys,threading,time\n"
        "threading.Thread(target=lambda: time.sleep(30),daemon=True).start()\n"
        "sys.stdout.write('ready\\n');sys.stdout.flush()\n"
        "sys.stdin.buffer.read()\n"
    )
    try:
        for _index in range(2):
            child = subprocess.Popen(
                [sys.executable, "-c", script], stdin=subprocess.PIPE, stdout=subprocess.PIPE
            )
            children.append(child)
            assert child.stdout is not None and child.stdout.readline() == b"ready\n"
        yield children[0], children[1]
    finally:
        for child in children:
            if child.poll() is None:
                os.kill(child.pid, signal.SIGCONT)
                child.terminate()
            child.wait(timeout=5)
            if child.stdin is not None:
                child.stdin.close()
            if child.stdout is not None:
                child.stdout.close()


def executable_sha(child: subprocess.Popen[bytes]) -> str:
    with Path(f"/proc/{child.pid}/exe").open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def pair(
    children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
) -> memory.OwnedNativePair:
    return memory.OwnedNativePair(
        *children,
        runtime_sha256=executable_sha(children[0]),
        client_sha256=executable_sha(children[1]),
    )


def test_exact_owned_pair_stops_every_thread_and_restores_after_read_failure(
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
) -> None:
    with pair(owned_children) as scope:
        with pytest.raises(RuntimeError, match="read failure"), scope.quiescent(timeout=2):
            assert len(scope.bindings) == 2
            for binding in scope.bindings:
                threads = memory.thread_census(binding)
                assert len(threads) >= 2 and all(row.state == "T" for row in threads)
                observation = memory.observe_process(binding)
                assert observation.rss_bytes > 0
                assert observation.start_time_ticks == binding.start_time_ticks
            raise RuntimeError("read failure")
        assert all(child.poll() is None for child in owned_children)
        assert all(
            all(row.state != "T" for row in memory.thread_census(binding))
            for binding in scope.bindings
        )


@pytest.fixture
def retiring_thread_children() -> Iterator[tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]]]:
    """Retire real worker threads on command, without replacing either process."""
    children = []
    script = (
        "import sys,threading\n"
        "release=threading.Event()\n"
        "worker=threading.Thread(target=release.wait,daemon=True);worker.start()\n"
        "print('ready',flush=True)\n"
        "for command in sys.stdin:\n"
        " if command.strip()=='retire':\n"
        "  release.set();worker.join();print('retired',flush=True)\n"
    )
    try:
        for _index in range(2):
            child = subprocess.Popen(
                [sys.executable, "-c", script], stdin=subprocess.PIPE, stdout=subprocess.PIPE
            )
            children.append(child)
            assert child.stdout is not None and child.stdout.readline() == b"ready\n"
        yield children[0], children[1]
    finally:
        for child in children:
            if child.poll() is None:
                os.kill(child.pid, signal.SIGCONT)
                child.terminate()
            child.wait(timeout=5)
            if child.stdin is not None:
                child.stdin.close()
            if child.stdout is not None:
                child.stdout.close()


@pytest.mark.parametrize("race", ["after-records", "missing-task-record"])
@pytest.mark.parametrize("phase", ["before-stop", "restoration"])
def test_real_worker_retirement_retries_only_verified_census_changes(
    retiring_thread_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
    race: str,
    phase: str,
) -> None:
    child = retiring_thread_children[0]
    task_directory = Path(f"/proc/{child.pid}/task")
    original_iterdir = Path.iterdir
    original_read = memory.read_kernel_record
    scans = 0
    retired = False
    armed = phase == "before-stop"

    def retire() -> None:
        nonlocal retired
        assert child.stdin is not None and child.stdout is not None
        child.stdin.write(b"retire\n")
        child.stdin.flush()
        assert child.stdout.readline() == b"retired\n"
        retired = True

    def tasks(path: Path) -> Iterator[Path]:
        nonlocal scans
        if path == task_directory and armed and not retired:
            scans += 1
            if race == "after-records" and scans == 2:
                retire()
        return original_iterdir(path)

    def records(path: Path, *, allow_empty: bool = False) -> bytes:
        if (
            armed
            and not retired
            and race == "missing-task-record"
            and path.parent.parent == task_directory
            and path.parent.name != str(child.pid)
            and path.name == "stat"
        ):
            retire()
        return original_read(path, allow_empty=allow_empty)

    monkeypatch.setattr(Path, "iterdir", tasks)
    monkeypatch.setattr(memory, "read_kernel_record", records)
    with pair(retiring_thread_children) as scope:
        original_signal = signal.pidfd_send_signal

        def signals(descriptor: int, sig: int, info: None, flags: int) -> None:
            nonlocal armed
            if descriptor == scope._pidfds[0] and sig == signal.SIGCONT:
                armed = True
            original_signal(descriptor, sig, info, flags)

        monkeypatch.setattr(signal, "pidfd_send_signal", signals)
        with scope.quiescent(timeout=2) as capture:
            assert len(capture.observe()) == 2
        assert retired
        assert all(child.poll() is None for child in retiring_thread_children)
        for binding in scope.bindings:
            assert all(row.state not in {"T", "t"} for row in memory.thread_census(binding))


def test_perpetual_census_changes_have_a_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    binding = memory.ProcessBinding(
        pid=17, start_time_ticks=123, role="engine-runtime", executable_sha256="a" * 64
    )
    calls = 0

    def changing(_binding: memory.ProcessBinding) -> tuple[memory.ThreadObservation, ...]:
        nonlocal calls
        calls += 1
        raise memory.ThreadCensusChanged("native thread census changed")

    monkeypatch.setattr(memory, "thread_census", changing)
    started = time.monotonic()
    with pytest.raises(memory.CaptureRefusal, match="stable thread census deadline"):
        memory.stable_thread_census(binding, started + 0.02)
    assert calls > 1 and time.monotonic() - started < 1


@pytest.mark.parametrize("error_number", [errno.ESRCH, errno.EACCES, errno.EIO])
def test_kernel_read_error_only_classifies_disappearance_as_missing(monkeypatch, error_number):
    class UnavailableRecord:
        def read(self, _limit):
            raise OSError(error_number, "Designed kernel read failure")

    @contextmanager
    def opening(_path, *_args, **_kwargs):
        yield UnavailableRecord()

    monkeypatch.setattr(Path, "open", opening)
    with pytest.raises(memory.CaptureRefusal) as refused:
        memory.read_kernel_record(Path("/proc/17/task/18/stat"))
    assert isinstance(refused.value, memory.KernelRecordMissing) is (error_number == errno.ESRCH)


def test_retired_open_record_retries_only_after_real_thread_membership_changes(
    retiring_thread_children, monkeypatch
):
    child = retiring_thread_children[0]
    task_directory = Path(f"/proc/{child.pid}/task")
    original_open = Path.open
    retired = False

    class RetiredRecord:
        def read(self, _limit):
            raise ProcessLookupError(errno.ESRCH, "Designed open proc record retired before read")

    @contextmanager
    def opening(path, *args, **kwargs):
        nonlocal retired
        with original_open(path, *args, **kwargs) as source:
            if (
                not retired
                and path.parent.parent == task_directory
                and path.parent.name != str(child.pid)
                and path.name == "stat"
            ):
                assert child.stdin is not None and child.stdout is not None
                child.stdin.write(b"retire\n")
                child.stdin.flush()
                assert child.stdout.readline() == b"retired\n"
                retired = True
                yield RetiredRecord()
            else:
                yield source

    monkeypatch.setattr(Path, "open", opening)
    with pair(retiring_thread_children) as scope:
        with scope.quiescent(timeout=2) as capture:
            assert len(capture.observe()) == 2
        assert retired
        assert all(child.poll() is None for child in retiring_thread_children)
        for binding in scope.bindings:
            assert all(row.state not in {"T", "t"} for row in memory.thread_census(binding))


def test_missing_worker_record_with_unchanged_membership_is_not_retried(
    retiring_thread_children, monkeypatch
):
    child = retiring_thread_children[0]
    task_directory = Path(f"/proc/{child.pid}/task")
    original_open = Path.open
    attempts = 0

    class MissingRecord:
        def read(self, _limit):
            raise ProcessLookupError(errno.ESRCH, "Designed unexplained missing worker record")

    @contextmanager
    def opening(path, *args, **kwargs):
        nonlocal attempts
        with original_open(path, *args, **kwargs) as source:
            if (
                path.parent.parent == task_directory
                and path.parent.name != str(child.pid)
                and path.name == "stat"
            ):
                attempts += 1
                yield MissingRecord()
            else:
                yield source

    with pair(retiring_thread_children) as scope:
        with monkeypatch.context() as patch:
            patch.setattr(Path, "open", opening)
            with pytest.raises(memory.KernelRecordMissing), scope.quiescent(timeout=2):
                pytest.fail("an unexplained missing record must not admit a sample")
        assert attempts == 1
        assert all(child.poll() is None for child in retiring_thread_children)
        for binding in scope.bindings:
            assert all(row.state not in {"T", "t"} for row in memory.thread_census(binding))


@pytest.mark.parametrize("reason", ["native PID incarnation differs", "permission refused"])
def test_census_security_refusals_are_never_retried(
    monkeypatch: pytest.MonkeyPatch, reason: str
) -> None:
    binding = memory.ProcessBinding(
        pid=17, start_time_ticks=123, role="engine-runtime", executable_sha256="a" * 64
    )
    calls = 0

    def refused(_binding: memory.ProcessBinding) -> tuple[memory.ThreadObservation, ...]:
        nonlocal calls
        calls += 1
        raise memory.CaptureRefusal(reason)

    monkeypatch.setattr(memory, "thread_census", refused)
    with pytest.raises(memory.CaptureRefusal, match=reason):
        memory.stable_thread_census(binding, time.monotonic() + 2)
    assert calls == 1


@pytest.mark.parametrize("body_fails", [False, True])
def test_opt_in_suspension_diagnostic_is_emitted_only_after_owned_children_resume(
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    body_fails: bool,
) -> None:
    monkeypatch.setenv("BABYLON_TIMINGS", "1")
    output = sys.stderr
    checked_writes = []
    with pair(owned_children) as native:

        class RestoredWriter:
            def write(self, text: str) -> int:
                assert all(
                    all(row.state not in {"T", "t"} for row in memory.thread_census(binding))
                    for binding in native.bindings
                ), "timing publication must occur after exact-child restoration"
                checked_writes.append(text)
                return output.write(text)

            def flush(self) -> None:
                output.flush()

        with monkeypatch.context() as context:
            context.setattr(sys, "stderr", RestoredWriter())
            now_ns = 1_000_000
            context.setattr(memory.time, "monotonic_ns", lambda: now_ns)
            try:
                with native.quiescent(timeout=2):
                    now_ns += 10_000_000
                    if body_fails:
                        raise RuntimeError("controlled observation refusal")
            except RuntimeError as error:
                assert body_fails and str(error) == "controlled observation refusal"
    records = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    assert len(records) == 1 and checked_writes
    record = records[0]
    assert record["version"] == 1
    assert record["scope"] == "sampler_timing_not_memory_qualification"
    assert record["stage"] == "NativeStopToRestoration"
    assert record["elapsed_ns"] == 10_000_000
    assert record["restored"] is True
    assert record["body_failed"] is body_fails
    assert "pid" not in record and "processes" not in record


def test_partial_stop_failure_resumes_both_exact_children(
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = memory.wait_native_stopped
    calls = 0

    def failing(
        binding: memory.ProcessBinding, deadline: float
    ) -> tuple[memory.ThreadObservation, ...]:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise memory.CaptureRefusal("second stop failed")
        return original(binding, deadline)

    monkeypatch.setattr(memory, "wait_native_stopped", failing)
    with pair(owned_children) as scope:
        with (
            pytest.raises(memory.CaptureRefusal, match="second stop failed"),
            scope.quiescent(timeout=2),
        ):
            pytest.fail("failed barrier cannot permit capture")
        for binding in scope.bindings:
            assert all(row.state != "T" for row in memory.thread_census(binding))


def test_one_capture_stabilizes_each_native_barrier_once(
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = memory.wait_native_stopped
    calls = []

    def counted(
        binding: memory.ProcessBinding, deadline: float
    ) -> tuple[memory.ThreadObservation, ...]:
        calls.append(binding.pid)
        return original(binding, deadline)

    monkeypatch.setattr(memory, "wait_native_stopped", counted)
    with pair(owned_children) as scope:
        with scope.quiescent(timeout=2) as capture:
            assert len(capture.observe()) == 2
        assert calls == [child.pid for child in owned_children]
        for binding in scope.bindings:
            assert all(row.state not in {"T", "t"} for row in memory.thread_census(binding))


@pytest.mark.parametrize("change", ["thread-start", "membership"])
def test_changed_frozen_native_census_refuses_and_restores(
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    original = memory.thread_census
    armed = False

    def census(binding: memory.ProcessBinding) -> tuple[memory.ThreadObservation, ...]:
        rows = original(binding)
        if armed and binding.pid == owned_children[0].pid and all(r.state == "T" for r in rows):
            first = rows[0]
            changed = memory.ThreadObservation(
                tid=first.tid if change == "thread-start" else max(r.tid for r in rows) + 1,
                start_time_ticks=first.start_time_ticks + 1,
                state="T",
                children=(),
            )
            return (changed, *rows[1:]) if change == "thread-start" else (*rows, changed)
        return rows

    monkeypatch.setattr(memory, "thread_census", census)
    with pair(owned_children) as scope:
        with (
            pytest.raises(memory.CaptureRefusal, match="frozen native thread census changed"),
            scope.quiescent(timeout=2),
        ):
            armed = True
        for binding in scope.bindings:
            assert all(row.state not in {"T", "t"} for row in original(binding))


def test_external_pre_stop_is_neither_admitted_nor_resumed(
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
) -> None:
    with pair(owned_children) as scope:
        binding = scope.bindings[0]
        os.kill(binding.pid, signal.SIGSTOP)
        memory.wait_native_stopped(binding, memory.time.monotonic() + 2)
        with (
            pytest.raises(memory.CaptureRefusal, match="already stopped"),
            scope.quiescent(timeout=2),
        ):
            pytest.fail("external stop must remain external")
        assert all(row.state == "T" for row in memory.thread_census(binding))


def test_wrong_executable_refuses_before_any_stop(
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
) -> None:
    with pytest.raises(memory.CaptureRefusal, match="executable"):
        memory.OwnedNativePair(*owned_children, runtime_sha256="a" * 64, client_sha256="a" * 64)
    assert all(child.poll() is None for child in owned_children)


def test_one_stopped_thread_cannot_establish_an_all_thread_barrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding = memory.ProcessBinding(
        pid=17, start_time_ticks=123, role="engine-runtime", executable_sha256="a" * 64
    )
    rows = (
        memory.ThreadObservation(tid=17, start_time_ticks=123, state="T", children=()),
        memory.ThreadObservation(tid=18, start_time_ticks=124, state="S", children=()),
    )
    monkeypatch.setattr(memory, "thread_census", lambda _binding: rows)
    with pytest.raises(memory.CaptureRefusal, match="all-thread"):
        memory.wait_native_stopped(binding, memory.time.monotonic() + 0.02)


def test_first_resume_failure_does_not_skip_other_child_or_hide_original(
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_signal = signal.pidfd_send_signal
    resumes = []

    def fail_first_resume(descriptor: int, sig: int, info: None, flags: int) -> None:
        if sig == signal.SIGCONT:
            resumes.append(descriptor)
            if len(resumes) == 1:
                raise PermissionError("specific restore refusal")
        original_signal(descriptor, sig, info, flags)

    with pair(owned_children) as scope:
        monkeypatch.setattr(signal, "pidfd_send_signal", fail_first_resume)
        failure = RuntimeError("original capture failure")
        with pytest.raises(BaseExceptionGroup) as result, scope.quiescent(timeout=2):
            raise failure
        assert result.value.exceptions[0] is failure
        assert len(resumes) == 2
        assert all(row.state != "T" for row in memory.thread_census(scope.bindings[0]))
        assert all(row.state == "T" for row in memory.thread_census(scope.bindings[1]))
        # Only this test's exact ledgered child is restored after the simulated denial.
        original_signal(scope._pidfds[1], signal.SIGCONT, None, 0)


def postgres_admission() -> memory.PostgresAdmission:
    return memory.PostgresAdmission(
        container_id="a" * 64,
        image_id="sha256:" + "b" * 64,
        host_pid=17,
        start_time_ticks=123,
        uid=70,
        gid=70,
        cgroup_directory=Path("/sys/fs/cgroup/owned"),
        cgroup_device=1,
        cgroup_inode=2,
        executable_sha256="c" * 64,
    )


def helper_frame(binding: memory.ProcessBinding) -> bytes:
    return (
        b"\n".join(
            [
                b"4026531837",
                str(binding.pid).encode(),
                b"4026531837",
                base64.b64encode(stat(binding.pid, binding.start_time_ticks)),
                f"{binding.executable_sha256}  /owned/{binding.pid}/exe".encode(),
                base64.b64encode(rollup()),
                base64.b64encode(stat(binding.pid, binding.start_time_ticks)),
            ]
        )
        + b"\n"
    )


def test_postgres_helper_authenticates_inode_namespace_and_exact_counters() -> None:
    binding = memory.ProcessBinding(
        pid=17, start_time_ticks=123, role="game-postgresql", executable_sha256="c" * 64
    )
    result = memory.decode_postgres_observations(helper_frame(binding), (binding,))
    assert result[0].role == "game-postgresql"
    assert result[0].rss_bytes == 12 * 1024
    for replacement in (
        helper_frame(binding).replace(b"4026531837\n17\n4026531837", b"4026531837\n17\n99999999"),
        helper_frame(binding).replace(b"c" * 64, b"a" * 64),
        helper_frame(binding).replace(b"\n17\n", b"\n18\n"),
        helper_frame(binding).replace(base64.b64encode(rollup()), b"not-base64"),
        helper_frame(binding) + b"extra\n",
    ):
        with pytest.raises(memory.CaptureRefusal):
            memory.decode_postgres_observations(replacement, (binding,))


def test_failed_pause_after_actual_freeze_is_reconciled_and_unpaused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A modeled Docker timeout after pause; no real Docker/PG is touched."""
    scope = memory.OwnedPostgresScope(postgres_admission(), lambda: None)
    paused = False
    commands = []

    def command(arguments: list[str], *, timeout: float) -> bytes:
        nonlocal paused
        commands.append(arguments[0])
        if arguments[0] == "pause":
            paused = True
            raise memory.CaptureRefusal("pause timed out after freezing")
        if arguments[0] == "unpause":
            paused = False
        return b""

    def state(_cid: str, *, timeout: float) -> memory.DockerState:
        return memory.DockerState(
            container_id="a" * 64,
            image_id="sha256:" + "b" * 64,
            host_pid=17,
            running=True,
            paused=paused,
        )

    monkeypatch.setattr(memory, "docker_command", command)
    monkeypatch.setattr(memory, "docker_state", state)
    monkeypatch.setattr(scope, "verify", lambda **_kwargs: (17,))
    with pytest.raises(memory.CaptureRefusal, match="pause timed out"), scope.quiescent(timeout=2):
        pytest.fail("a failed pause must not publish a sample")
    assert commands == ["pause", "unpause"] and not paused


def test_postgres_helper_failure_unpauses_and_preserves_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = memory.OwnedPostgresScope(postgres_admission(), lambda: None)
    paused = False

    def command(arguments: list[str], *, timeout: float) -> bytes:
        nonlocal paused
        paused = arguments[0] == "pause"
        return b""

    def state(_cid: str, *, timeout: float) -> memory.DockerState:
        return memory.DockerState(
            container_id="a" * 64,
            image_id="sha256:" + "b" * 64,
            host_pid=17,
            running=True,
            paused=paused,
        )

    monkeypatch.setattr(memory, "docker_command", command)
    monkeypatch.setattr(memory, "docker_state", state)
    monkeypatch.setattr(scope, "verify", lambda **_kwargs: (17,))
    monkeypatch.setattr(memory, "read_kernel_record", lambda _path: stat())
    monkeypatch.setattr(memory, "verify_process_credentials", lambda *_args: None)
    with pytest.raises(RuntimeError, match="helper failed"), scope.quiescent(timeout=2):
        assert paused
        raise RuntimeError("helper failed")
    assert not paused


@pytest.mark.parametrize(
    "transition", ["founding", "advance", "foundation", "regression", "hash", "restore"]
)
def test_crossing_capture_is_unassigned_only_after_normal_publication_and_restoration(
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
    transition: str,
) -> None:
    """Actual native children, modeled PostgreSQL barrier and committed markers."""
    pg = memory.OwnedPostgresScope(postgres_admission(), lambda: None)
    binding = memory.ProcessBinding(
        pid=17, start_time_ticks=123, role="game-postgresql", executable_sha256="c" * 64
    )

    @contextmanager
    def pg_barrier(*, timeout: float) -> Iterator[tuple[memory.ProcessBinding, ...]]:
        yield (binding,)

    monkeypatch.setattr(pg, "quiescent", pg_barrier)
    monkeypatch.setattr(
        pg,
        "observe",
        lambda bindings, **_kwargs: memory.decode_postgres_observations(
            helper_frame(binding), bindings
        ),
    )
    before = memory.CampaignMemoryMarker(
        campaign="81b979ee-a9c1-48fd-8835-06cbfe594675",
        foundation_sha256=None if transition == "founding" else "a" * 64,
        campaign_age_ticks=0 if transition == "founding" else 1,
        tick_content_hash=None if transition == "founding" else "b" * 64,
    )
    after = memory.CampaignMemoryMarker(
        campaign=before.campaign,
        foundation_sha256="d" * 64 if transition == "foundation" else "a" * 64,
        campaign_age_ticks=0
        if transition in {"founding", "regression"}
        else (1 if transition == "hash" else 2),
        tick_content_hash=None if transition in {"founding", "regression"} else "c" * 64,
    )
    markers = iter([before, after])
    with pair(owned_children) as native:
        original_quiescent = native.quiescent

        @contextmanager
        def restore_refusal(*, timeout: float):
            with original_quiescent(timeout=timeout) as capture:
                yield capture
            raise memory.CaptureRefusal("native restoration refused")

        if transition == "restore":
            monkeypatch.setattr(native, "quiescent", restore_refusal)
        error_type = (
            memory.PublicationAdvanced
            if transition in {"founding", "advance"}
            else memory.CaptureRefusal
        )
        with pytest.raises(error_type) as refused:
            memory.collect_running_game(
                native,
                pg,
                lambda: next(markers),
                campaign="81b979ee-a9c1-48fd-8835-06cbfe594675",
                foundation_sha256=before.foundation_sha256,
                sequence=1,
                timeout=2,
            )
        if transition in {"founding", "advance"}:
            record = refused.value.record
            assert record.before == before and record.after == after
            assert {process.role for process in record.processes} == {
                "native-client",
                "engine-runtime",
                "game-postgresql",
            }
            assert record.capture_duration_ns >= 0
        elif transition == "restore":
            assert str(refused.value) == "native restoration refused"
        else:
            assert not isinstance(refused.value, memory.PublicationAdvanced)
        assert all(
            all(row.state != "T" for row in memory.thread_census(binding))
            for binding in native.bindings
        )


def test_periodic_publication_crossing_retains_diagnostic_and_continues(
    tmp_path, owned_children, monkeypatch
):
    capture = capture_runner(tmp_path, owned_children)
    calls = 0

    def collect(*_args, **kwargs):
        nonlocal calls
        calls += 1
        batch = synthetic_batch(int(kwargs["sequence"]), 1)
        if calls == 1:
            raise memory.PublicationAdvanced(
                memory.UnassignedMemoryCapture(
                    version=1,
                    scope="unassigned_capture_not_memory_qualification",
                    boot_id=batch.boot_id,
                    before=memory.CampaignMemoryMarker(
                        campaign=capture._campaign,
                        foundation_sha256="a" * 64,
                        campaign_age_ticks=0,
                        tick_content_hash=None,
                    ),
                    after=memory.CampaignMemoryMarker(
                        campaign=capture._campaign,
                        foundation_sha256="a" * 64,
                        campaign_age_ticks=1,
                        tick_content_hash="b" * 64,
                    ),
                    monotonic_ns=batch.sample.monotonic_ns,
                    capture_duration_ns=batch.sample.capture_duration_ns,
                    processes=batch.sample.processes,
                )
            )
        return batch

    monkeypatch.setattr(memory, "collect_running_game", collect)
    capture._gap = 0.01
    with capture.lifecycle(*owned_children) as monitor:
        wait_for(lambda: len(capture._samples) >= 1 or capture._failure is not None)
        monitor.check()
        monitor.finish()
    diagnostics = list((tmp_path / "memory-unassigned").glob("*.json"))
    assert len(diagnostics) == 1
    diagnostic = json.loads(diagnostics[0].read_bytes())
    assert diagnostic["scope"] == "unassigned_capture_not_memory_qualification"
    assert diagnostic["before"]["campaign_age_ticks"] == 0
    assert diagnostic["after"]["campaign_age_ticks"] == 1
    with pytest.raises(ValidationError):
        memory.MemorySample.model_validate(diagnostic)
    result = memory.CombinedMemoryEvidence.model_validate_json(
        (tmp_path / "combined-memory.json").read_bytes()
    )
    assert all(sample.campaign_age_ticks == 1 for sample in result.samples)
    progress = json.loads((tmp_path / "combined-memory-progress.json").read_bytes())
    assert progress["unassigned_capture_count"] == 1 and not progress["capture_failed"]


@pytest.mark.parametrize("boundary", ["startup", "final"])
def test_required_memory_capture_does_not_accept_an_unassigned_publication_crossing(
    tmp_path, owned_children, monkeypatch, boundary
):
    capture = capture_runner(
        tmp_path, owned_children, foundation=None if boundary == "startup" else "a" * 64
    )
    refuse = boundary == "startup"

    def collect(*_args, **kwargs):
        batch = synthetic_batch(int(kwargs["sequence"]), 1)
        if refuse:
            before = memory.CampaignMemoryMarker(
                campaign=capture._campaign,
                foundation_sha256=None if boundary == "startup" else "a" * 64,
                campaign_age_ticks=0 if boundary == "startup" else 1,
                tick_content_hash=None if boundary == "startup" else "b" * 64,
            )
            after = memory.CampaignMemoryMarker(
                campaign=capture._campaign,
                foundation_sha256="a" * 64,
                campaign_age_ticks=0 if boundary == "startup" else 2,
                tick_content_hash=None if boundary == "startup" else "c" * 64,
            )
            raise memory.PublicationAdvanced(
                memory.UnassignedMemoryCapture(
                    version=1,
                    scope="unassigned_capture_not_memory_qualification",
                    boot_id=batch.boot_id,
                    before=before,
                    after=after,
                    monotonic_ns=batch.sample.monotonic_ns,
                    capture_duration_ns=batch.sample.capture_duration_ns,
                    processes=batch.sample.processes,
                )
            )
        return batch

    monkeypatch.setattr(memory, "collect_running_game", collect)
    with pytest.raises(BaseException) as refused, capture.lifecycle(*owned_children) as monitor:
        wait_for(lambda: bool(capture._samples))
        refuse = True
        monitor.finish()
    assert any(
        isinstance(error, memory.PublicationAdvanced) for error in leaf_errors(refused.value)
    )
    assert not (tmp_path / "combined-memory.json").exists()


def test_running_capture_authenticates_each_exact_child_executable_once_per_lifetime(
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real native barriers revalidate the authenticated, immutable running inode."""
    pg = memory.OwnedPostgresScope(postgres_admission(), lambda: None)
    binding = memory.ProcessBinding(
        pid=17, start_time_ticks=123, role="game-postgresql", executable_sha256="c" * 64
    )

    @contextmanager
    def pg_barrier(*, timeout: float) -> Iterator[tuple[memory.ProcessBinding, ...]]:
        yield (binding,)

    monkeypatch.setattr(pg, "quiescent", pg_barrier)
    monkeypatch.setattr(
        pg,
        "observe",
        lambda bindings, **_kwargs: memory.decode_postgres_observations(
            helper_frame(binding), bindings
        ),
    )
    marker = memory.CampaignMemoryMarker(
        campaign="81b979ee-a9c1-48fd-8835-06cbfe594675",
        foundation_sha256="a" * 64,
        campaign_age_ticks=1,
        tick_content_hash="b" * 64,
    )
    original_digest = hashlib.file_digest
    reads = []

    def counted_digest(source: BinaryIO, algorithm: str) -> object:
        reads.append(source.name)
        return original_digest(source, algorithm)

    digests = tuple(executable_sha(child) for child in owned_children)
    monkeypatch.setattr(hashlib, "file_digest", counted_digest)
    with memory.OwnedNativePair(
        *owned_children, runtime_sha256=digests[0], client_sha256=digests[1]
    ) as native:
        for sequence in (1, 2):
            native.verify()
            result = memory.collect_running_game(
                native,
                pg,
                lambda: marker,
                campaign=marker.campaign,
                foundation_sha256=marker.foundation_sha256,
                sequence=sequence,
                timeout=2,
            )
            assert len(result.sample.processes) == 3
            assert all(row.rss_bytes > 0 for row in result.sample.processes)
            assert reads == [f"/proc/{child.pid}/exe" for child in owned_children]


@pytest.mark.parametrize("field", ["device", "inode", "size", "modified_ns", "changed_ns"])
def test_native_lifetime_witness_refuses_identity_changes_between_captures(
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    original_identity = memory._executable_identity

    def changed_identity(path: Path) -> memory._ExecutableIdentity:
        original = original_identity(path)
        return replace(original, **{field: getattr(original, field) + 1})

    with pair(owned_children) as native:
        with native.quiescent(timeout=2) as capture:
            assert len(capture.observe()) == 2
        monkeypatch.setattr(memory, "_executable_identity", changed_identity)
        with pytest.raises(memory.CaptureRefusal, match="executable changed during capture"):
            native.verify()
        with (
            pytest.raises(memory.CaptureRefusal, match="executable changed during capture"),
            native.quiescent(timeout=2),
        ):
            pytest.fail("a changed lifetime witness must refuse before capture")
        for binding in native.bindings:
            assert all(row.state not in {"T", "t"} for row in memory.thread_census(binding))


def test_authenticated_native_observation_expires_with_the_owning_capture(
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
) -> None:
    with pair(owned_children) as native:
        with native.quiescent(timeout=2) as capture:
            assert len(capture.observe()) == 2
            assert len(capture.observe()) == 2
            refused = []

            def other_thread() -> None:
                try:
                    capture.observe()
                except memory.CaptureRefusal as error:
                    refused.append(str(error))

            thread = threading.Thread(target=other_thread)
            thread.start()
            thread.join(timeout=1)
            assert not thread.is_alive() and refused == [
                "native observation requires its active owning capture"
            ]
        with pytest.raises(memory.CaptureRefusal, match="active owning capture"):
            capture.observe()


def test_running_native_executable_inode_cannot_be_opened_for_mutation(
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
) -> None:
    """Linux denies writes to the actual executable; path replacement changes inode."""
    for child in owned_children:
        descriptor = None
        try:
            descriptor = os.open(f"/proc/{child.pid}/exe", os.O_WRONLY)
        except OSError as error:
            assert error.errno == errno.ETXTBSY
        else:
            pytest.fail("running executable must remain protected against writes")
        finally:
            if descriptor is not None:
                os.close(descriptor)


@pytest.mark.parametrize("field", ["device", "inode", "size", "modified_ns", "changed_ns"])
def test_authenticated_native_observation_refuses_changed_file_identity(
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    original_identity = memory._executable_identity

    def changed_identity(path: Path) -> memory._ExecutableIdentity:
        original = original_identity(path)
        return replace(original, **{field: getattr(original, field) + 1})

    with pair(owned_children) as native:
        with (
            pytest.raises(memory.CaptureRefusal, match="changed during capture"),
            native.quiescent(timeout=2) as capture,
        ):
            monkeypatch.setattr(memory, "_executable_identity", changed_identity)
            capture.observe()
        assert all(
            all(row.state != "T" for row in memory.thread_census(binding))
            for binding in native.bindings
        )


def test_authenticated_native_observation_refuses_changed_process_incarnation(
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_read = memory.read_kernel_record
    changed = False
    injected = False

    def changed_read(path: Path, *, allow_empty: bool = False) -> bytes:
        nonlocal changed, injected
        record = original_read(path, allow_empty=allow_empty)
        if path.name == "smaps_rollup":
            changed = True
        elif changed and not injected and path.name == "stat":
            injected = True
            prefix, suffix = record.rsplit(b")", 1)
            fields = suffix.split()
            fields[19] = str(int(fields[19]) + 1).encode()
            return prefix + b") " + b" ".join(fields) + b"\n"
        return record

    with pair(owned_children) as native:
        with (
            pytest.raises(memory.CaptureRefusal, match="incarnation differs"),
            native.quiescent(timeout=2) as capture,
        ):
            monkeypatch.setattr(memory, "read_kernel_record", changed_read)
            capture.observe()
        assert injected
        assert all(
            all(row.state != "T" for row in memory.thread_census(binding))
            for binding in native.bindings
        )


def frozen_capture_files(directory: Path) -> dict[str, str]:
    policy = (
        Path(__file__).resolve().parents[3] / "contracts/national_storage_qualification_v6.json"
    )
    result = {}
    for key, name in memory.CAPTURE_FILES.items():
        data = (
            policy.read_bytes() if name == "policy.json" else b"synthetic frozen runner admission"
        )
        (directory / name).write_bytes(data)
        result[key] = hashlib.sha256(data).hexdigest()
    return result


def synthetic_batch(sequence: int, age: int) -> memory.QuiescentBatch:
    binding = memory.ProcessBinding(
        pid=17, start_time_ticks=123, role="game-postgresql", executable_sha256="c" * 64
    )
    return memory.QuiescentBatch(
        boot_id="00000000-0000-0000-0000-000000000001",
        sample=memory.MemorySample(
            sequence=sequence,
            foundation_sha256="a" * 64,
            campaign_age_ticks=age,
            tick_content_hash="b" * 64 if age else None,
            monotonic_ns=time.monotonic_ns(),
            capture_duration_ns=0,
            simultaneous_capture="owned_game_group_stopped",
            roster_complete="all_game_processes_in_owned_scope",
            native_client_mode="windowed",
            processes=memory.decode_postgres_observations(helper_frame(binding), (binding,)),
        ),
    )


def wait_for(predicate: Callable[[], bool]) -> None:
    deadline = time.monotonic() + 3
    while not predicate():
        assert time.monotonic() < deadline, "bounded collector observation timed out"
        # Poll only until the explicit three-second collector deadline.
        time.sleep(0.005)  # nosemgrep: babylon.determinism.no-wall-clock-sleep-in-tests


def capture_runner(
    directory: Path,
    children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    operation_lock: AbstractContextManager[object] | None = None,
    foundation: str | None = "a" * 64,
) -> memory.RunningMemoryCapture:
    return memory.RunningMemoryCapture(
        directory=directory,
        expected_hashes=frozen_capture_files(directory),
        campaign="81b979ee-a9c1-48fd-8835-06cbfe594675",
        foundation_sha256=foundation,
        runtime_sha256=executable_sha(children[0]),
        client_sha256=executable_sha(children[1]),
        postgres=memory.OwnedPostgresScope(postgres_admission(), lambda: None),
        read_marker=lambda: memory.CampaignMemoryMarker(
            campaign="81b979ee-a9c1-48fd-8835-06cbfe594675",
            foundation_sha256="a" * 64,
            campaign_age_ticks=0,
            tick_content_hash=None,
        ),
        sample_gap_seconds=5,
        operation_timeout=2,
        operation_lock=operation_lock,
    )


@pytest.mark.parametrize("failure", [None, "counter", "cancelled"])
def test_counter_interval_is_bracketed_and_evidence_waits_for_native_restore(
    tmp_path: Path,
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
    failure: str | None,
) -> None:
    collector = capture_runner(tmp_path, owned_children)
    events: list[str] = []
    binding = memory.ProcessBinding(
        pid=17, start_time_ticks=123, role="game-postgresql", executable_sha256="c" * 64
    )

    def native_running() -> None:
        for child in owned_children:
            row = memory.ProcessBinding(
                pid=child.pid,
                start_time_ticks=memory.parse_start_time(
                    memory.read_kernel_record(Path(f"/proc/{child.pid}/stat")), child.pid
                ),
                role="engine-runtime",
                executable_sha256=executable_sha(child),
            )
            assert all(thread.state != "T" for thread in memory.thread_census(row))

    @contextmanager
    def pg_barrier(*, timeout: float) -> Iterator[tuple[memory.ProcessBinding, ...]]:
        events.append("postgres-stopped")
        try:
            yield (binding,)
        finally:
            events.append("postgres-restored")

    def observe(bindings, **_kwargs):
        if failure == "counter":
            raise memory.CaptureRefusal("counter refused")
        if failure == "cancelled":
            raise KeyboardInterrupt
        return memory.decode_postgres_observations(helper_frame(binding), bindings)

    original_marker = collector._read_marker

    def marker():
        events.append("marker")
        return original_marker()

    original_write = memory.write_capture_record

    def write(destination, record):
        native_running()
        events.append("evidence-written")
        original_write(destination, record)

    collector._read_marker = marker
    monkeypatch.setattr(collector._postgres, "quiescent", pg_barrier)
    monkeypatch.setattr(collector._postgres, "observe", observe)
    monkeypatch.setattr(memory, "write_capture_record", write)
    with pair(owned_children) as native:
        if failure:
            with pytest.raises(
                KeyboardInterrupt if failure == "cancelled" else memory.CaptureRefusal
            ):
                collector._capture_one(native)
            assert not collector._samples
        else:
            collector._capture_one(native)
            assert len(collector._samples) == 1
    assert events[0] == "marker"
    assert events.count("marker") == (1 if failure else 2)
    if failure:
        assert events[-1] == "postgres-restored" and "evidence-written" not in events
    else:
        assert events.index("postgres-restored") < len(events) - 2
        assert events[-1] == "evidence-written"


def test_startup_marker_records_absence_without_creating_a_foundation() -> None:
    marker = memory.CampaignMemoryMarker(
        campaign="81b979ee-a9c1-48fd-8835-06cbfe594675",
        foundation_sha256=None,
        campaign_age_ticks=0,
        tick_content_hash=None,
    )
    assert marker.foundation_sha256 is None
    with pytest.raises(ValueError):
        memory.CampaignMemoryMarker(
            campaign=marker.campaign,
            foundation_sha256=None,
            campaign_age_ticks=1,
            tick_content_hash="b" * 64,
        )


def test_startup_capture_finishes_absent_sample_before_releasing_the_driver(
    tmp_path: Path,
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Modeled marker transitions exercise the actual publisher and real owned pair."""
    foundation: str | None = None
    age = 0

    def collect(*_args: object, **kwargs: object) -> memory.QuiescentBatch:
        batch = synthetic_batch(int(kwargs["sequence"]), age)
        raw = batch.model_dump(mode="json")
        raw["sample"]["foundation_sha256"] = foundation
        return memory.QuiescentBatch.model_validate(raw)

    monkeypatch.setattr(memory, "collect_running_game", collect)
    capture = capture_runner(tmp_path, owned_children, foundation=None)
    with capture.lifecycle(*owned_children) as monitor:
        assert capture._samples[0].foundation_sha256 is None
        first_bytes = (tmp_path / "memory-samples/00000001.json").read_bytes()
        foundation = "a" * 64
        # Actual PostgreSQL may commit before the native acknowledgment arrives.
        assert capture._native is not None
        capture._capture_one(capture._native)
        monitor.bind_foundation(foundation)
        assert (tmp_path / "memory-samples/00000001.json").read_bytes() == first_bytes
        age = 1
        monitor.finish()
        result = memory.CombinedMemoryEvidence.model_validate_json(
            (tmp_path / "combined-memory.json").read_bytes()
        )
        assert result.version == 2
        assert result.samples[0].foundation_sha256 is None
        assert all(s.foundation_sha256 == foundation for s in result.samples[1:])


def test_worker_start_refusal_exits_and_preserves_the_original_failure(
    tmp_path: Path,
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture = capture_runner(tmp_path, owned_children)
    admitted = threading.Event()
    finished = threading.Event()
    errors: list[BaseException] = []
    refusal = RuntimeError("cannot start owned sampler thread")

    def exercise() -> None:
        admitted.wait(2)
        try:
            with capture.lifecycle(*owned_children):
                raise AssertionError("refused startup cannot release the driver")
        except BaseException as error:
            errors.append(error)
        finally:
            finished.set()

    observer = threading.Thread(target=exercise, daemon=True)
    observer.start()

    def reject(_thread: threading.Thread) -> None:
        raise refusal

    monkeypatch.setattr(threading.Thread, "start", reject)
    admitted.set()
    try:
        assert finished.wait(2), "unstarted worker cannot acknowledge cleanup"
    finally:
        # Bound the deliberately broken RED path: this token releases only the
        # modeled unstarted worker, never a live collector or native barrier.
        if not finished.is_set():
            capture._worker_finished.set()
        observer.join(2)
    assert not observer.is_alive()
    assert refusal in leaf_errors(errors[0])
    assert all(child.poll() is None for child in owned_children)
    assert capture._native is not None and not capture._native._pidfds


def test_pending_sigint_after_worker_creation_drains_the_actual_worker(
    tmp_path: Path,
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture = capture_runner(tmp_path, owned_children)
    monkeypatch.setattr(
        memory, "collect_running_game", lambda *_args, **kw: synthetic_batch(kw["sequence"], 1)
    )
    original = threading.Thread.start

    def cancel_started(thread: threading.Thread) -> None:
        original(thread)
        signal.raise_signal(signal.SIGINT)

    monkeypatch.setattr(threading.Thread, "start", cancel_started)
    with pytest.raises(BaseException) as failure, capture.lifecycle(*owned_children):
        raise AssertionError("cancellation cannot release the native driver")
    assert any(isinstance(leaf, KeyboardInterrupt) for leaf in leaf_errors(failure.value))
    assert capture._thread is not None and not capture._thread.is_alive()
    assert capture._native is not None and not capture._native._pidfds
    assert all(child.poll() is None for child in owned_children)


def test_supervisor_reader_lock_excludes_the_owned_pause_operation(
    tmp_path: Path,
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real capture thread cannot enter its barrier across an admitted reader."""
    lock = threading.RLock()
    attempted = threading.Event()
    collected = threading.Event()

    def collect(*_args: object, **kwargs: object) -> memory.QuiescentBatch:
        collected.set()
        return synthetic_batch(int(kwargs["sequence"]), 1)

    monkeypatch.setattr(memory, "collect_running_game", collect)

    class ReaderAdmission:
        def __enter__(self):
            if threading.current_thread() is not threading.main_thread():
                attempted.set()
            lock.acquire()
            return self

        def __exit__(self, *_args):
            lock.release()

    capture = capture_runner(tmp_path, owned_children, operation_lock=ReaderAdmission())
    lock.acquire()
    with capture.lifecycle(*owned_children) as monitor:
        try:
            assert attempted.wait(2), "capture worker did not attempt the owned operation"
            assert not collected.wait(0.25), "capture crossed the admitted supervisor read"
        finally:
            lock.release()
        assert collected.wait(2), "capture did not resume after the supervisor released the lock"
        monitor.finish()
    assert capture._thread is not None and not capture._thread.is_alive()


def test_periodic_publisher_retains_prefix_and_captures_final_boundary_before_quit(
    tmp_path: Path,
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Modeled kernel batches exercise the real producer; no game qualification."""
    age = 0
    monkeypatch.setattr(
        memory, "collect_running_game", lambda *_args, **kw: synthetic_batch(kw["sequence"], age)
    )
    capture = capture_runner(tmp_path, owned_children)
    with capture.lifecycle(*owned_children) as monitor:
        wait_for(lambda: bool(capture._samples))
        progress = json.loads((tmp_path / "combined-memory-progress.json").read_bytes())
        assert progress["status"] == "incomplete"
        assert (tmp_path / "memory-samples/00000001.json").is_file()
        age = 1
        monitor.finish()
        result = memory.CombinedMemoryEvidence.model_validate_json(
            (tmp_path / "combined-memory.json").read_bytes()
        )
        assert result.periods == 1
        assert [sample.campaign_age_ticks for sample in result.samples] == [0, 1]
        assert (tmp_path / "memory-samples/00000002.json").is_file()
        assert all(child.poll() is None for child in owned_children)
    assert capture._thread is not None and not capture._thread.is_alive()


def test_cancellation_after_kernel_accepts_stop_restores_attempted_child(
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = signal.pidfd_send_signal

    def cancel(descriptor: int, sig: int, info: None, flags: int) -> None:
        original(descriptor, sig, info, flags)
        if sig == signal.SIGSTOP:
            raise KeyboardInterrupt("cancel immediately after accepted stop")

    with pair(owned_children) as scope:
        monkeypatch.setattr(signal, "pidfd_send_signal", cancel)
        with pytest.raises(KeyboardInterrupt), scope.quiescent(timeout=2):
            pytest.fail("canceled acquisition cannot permit capture")
        assert all(
            all(row.state != "T" for row in memory.thread_census(binding))
            for binding in scope.bindings
        )


def test_helper_scope_is_fixed_and_cancellation_removes_only_authenticated_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands = []
    helper_id = "d" * 64
    owner = "e" * 32
    monkeypatch.setattr(memory, "uuid4", lambda: memory.UUID(owner))

    def command(arguments: list[str], *, timeout: float) -> bytes:
        commands.append(arguments)
        if arguments[0] == "run":
            Path(arguments[arguments.index("--cidfile") + 1]).write_text(helper_id)
            assert "--pid" not in arguments and "--privileged" not in arguments
            assert arguments[arguments.index("--user") + 1] == "70:70"
            assert arguments[arguments.index("--network") + 1] == "none"
            mounts = [
                arguments[index + 1] for index, value in enumerate(arguments) if value == "--mount"
            ]
            assert mounts == [
                "type=tmpfs,destination=/var/lib/postgresql/data,tmpfs-size=1048576",
                "type=bind,source=/proc/17,destination=/owned/17,readonly",
            ]
            script = arguments[arguments.index("-c") + 1]
            assert all(
                value not in script for value in ("/environ", "/fd", "/root", "find ", "ls ")
            )
            raise KeyboardInterrupt("helper canceled after creation")
        if arguments[0] == "ps":
            return helper_id.encode() + b"\n"
        if arguments[0:2] == ["container", "inspect"]:
            return f"{owner}|sha256:{'b' * 64}\n".encode()
        if arguments[0:2] == ["container", "rm"]:
            assert arguments == ["container", "rm", "--force", helper_id]
            return b""
        pytest.fail("unexpected helper operation")

    monkeypatch.setattr(memory, "docker_command", command)
    scope = memory.OwnedPostgresScope(postgres_admission(), lambda: None)
    binding = memory.ProcessBinding(
        pid=17, start_time_ticks=123, role="game-postgresql", executable_sha256="c" * 64
    )
    with pytest.raises(KeyboardInterrupt, match="helper canceled"):
        scope.observe((binding,), timeout=2)
    assert commands[-1] == ["container", "rm", "--force", helper_id]


def leaf_errors(error: BaseException) -> list[BaseException]:
    if isinstance(error, BaseExceptionGroup):
        return [leaf for child in error.exceptions for leaf in leaf_errors(child)]
    return [error]


def test_capture_failure_is_preserved_when_progress_publication_also_fails(
    tmp_path: Path,
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture = capture_runner(tmp_path, owned_children)
    capture_failure = memory.CaptureRefusal("original counter refusal")
    publication_failure = OSError("progress publication refused")
    capture._failure = capture_failure

    def refuse() -> None:
        raise publication_failure

    monkeypatch.setattr(capture, "_progress", refuse)
    with pytest.raises(BaseExceptionGroup) as error:
        capture.finish()
    leaves = leaf_errors(error.value)
    assert capture_failure in leaves and publication_failure in leaves


def test_canceled_capture_drain_waits_until_real_native_stop_has_unwound(
    tmp_path: Path,
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stopped = threading.Event()
    release = threading.Event()
    canceled = KeyboardInterrupt("cancel during collector drain")

    def held_capture(
        native: memory.OwnedNativePair, *_args: object, **kwargs: object
    ) -> memory.QuiescentBatch:
        with native.quiescent(timeout=2):
            stopped.set()
            assert release.wait(2), "test did not release its exact native barrier"
        return synthetic_batch(kwargs["sequence"], 1)

    monkeypatch.setattr(memory, "collect_running_game", held_capture)
    capture = capture_runner(tmp_path, owned_children)
    original_wait = capture._worker_finished.wait
    interrupted = False

    def interrupt_once(timeout: float | None = None) -> bool:
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise canceled
        return original_wait(timeout)

    monkeypatch.setattr(capture._worker_finished, "wait", interrupt_once)
    timer = threading.Timer(0.1, release.set)
    try:
        with (
            pytest.raises(BaseExceptionGroup) as error,
            capture.lifecycle(*owned_children) as monitor,
        ):
            assert stopped.wait(2)
            timer.start()
            monitor.finish()
        assert canceled in leaf_errors(error.value)
        assert capture._native is not None and not capture._native._capture_lock.locked()
        for child in owned_children:
            assert child.poll() is None
        assert capture._thread is not None and not capture._thread.is_alive()
    finally:
        release.set()
        if timer.ident is not None:
            timer.join(2)
        if capture._thread is not None:
            capture._thread.join(3)


def test_periodic_capture_failure_is_visible_to_driver_and_never_publishes_result(
    tmp_path: Path,
    owned_children: tuple[subprocess.Popen[bytes], subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failure = memory.CaptureRefusal("kernel record refused")

    def refuse(*_args: object, **_kwargs: object) -> memory.QuiescentBatch:
        raise failure

    monkeypatch.setattr(memory, "collect_running_game", refuse)
    capture = capture_runner(tmp_path, owned_children)
    with (
        pytest.raises(memory.CaptureRefusal) as error,
        capture.lifecycle(*owned_children) as monitor,
    ):
        wait_for(lambda: capture._failure is not None)
        monitor.check()
    assert error.value is failure
    assert not (tmp_path / "combined-memory.json").exists()
    assert json.loads((tmp_path / "combined-memory-progress.json").read_bytes())["capture_failed"]
    assert capture._thread is not None and not capture._thread.is_alive()
