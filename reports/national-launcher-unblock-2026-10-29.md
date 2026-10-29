# National launcher installation check: 2026-10-29

The real Rust runtime and client passed the standard and national installation
checks through the Python launcher and a disposable Postgres instance. The
launcher accepts the current economy status schema `2` and checks typed
identity, scope, period and hash evidence. It refuses unsupported schema values.

The qualified Rust base was `b873060e9289f51bcd1392d5d796c88be93d4988`.
The qualification used Python, workflow and test changes before their commit.
The file hashes below identify their tested bytes. The separate cold build of
the unchanged runtime and client finished in `18m04s` before the harness run.
That build is not an interactive latency measurement.

## Disposable session evidence

Command: `BLAS=1 BABYLON_POSTGRES_LIVE_FOCUS=session_progress mise run test:rust-postgres`.
It exited `0`. The local log is
`.superpowers/sdd/2026-10-29-national-launcher-contract/session-progress.log`.
Both campaigns committed period `1`, restarted and reopened without defines.

| Preset | Campaign | Foundation digest | Tick content hash |
| --- | --- | --- | --- |
| `standard` | `677460ea-d8a8-402f-8fab-c64669e2d68b` | `9a15feda30d45f61815ae9551ec18fa3fb89a5270218adfb1fd6804b3b69c61a` | `9a1e442051869abb1e1d90bee9a291d5153f13d37b8cde2678a72deda1f4e8f5` |
| `national-world` | `c149793a-f81e-46da-b79f-605d63f4a19c` | `be8c2f21b7ea3093850a88df5029acb5c221f6b23cd6225e539306b7861f5fc6` | `eb22d0f0c83160abcd74904ff382a5c5792efd89ba01564823c892b0b3fca700` |

The national reader reported `3144` counties, `3144` domestic and `18`
external household locations, `60634` sites and `15696` household cohorts.
It reported the exact national roster, household coverage of that roster and
completed material balance. It returned `28293` completed goods accounts,
`59685` completed service accounts and `18317` price accounts. Its campaign,
foundation and tick identity matched the lifecycle response.

- Nominal world hash: `e43f172b439a2b682db0dcea59971104dd7c28e41d850d1a3cb055dc4a7a4193`
- Envelope digest: `d1af4533605ea7b32211e014fa6e48cfc4e16ab628f82c8a5e685e751422a131`
- Production evidence SHA-256: `6878018b2fb44196e46ab567b940d3fb072b1333c0e27ef22279ea7f8b7c96c5`

The national phase took `370s` of its `600s` limit. Its opening, advance and
reopen took `109.451613s`, `68.102893s` and `78.892132s`. The economy read
took `100.573247s`. The standard phase took `37s`. The full harness took
`784s` and verified cleanup of container `babylon-runtime-pg-7e59a5e9ef56`
and volume `1cc9960d7aee7e09bfe959ddee643f377c2bd2c58fbe55190f8b3e2ae2c5e547`.

These latencies remain a material limitation under `PER-360`. This run does not
prove sustained national resource budgets or human acceptance of native play.
The new weekly focus will run both installation checks after merge. No hosted
run of that change has occurred yet.

## Other checks

`BLAS=1 mise run check` passed: `3253` tests, `18` skips, `390` formatted
files and `55` mypy files. Scoped checks passed for `155` launcher tests,
`20` runner tests and `57` bootstrap and CI tests. Code and CI review passed.

actionlint and warning-level ShellCheck passed at qualification. Afterward, the
team added narrow ShellCheck annotations to the runner. The pinned default
hook, ShellCheck with `-x` and Bash syntax checks passed, as did the `20` runner
tests. The team corrected the initial touched-file format failure before the
passing gate.

## Qualified file SHA-256

| File | SHA-256 |
| --- | --- |
| `.github/actions/bootstrap-persistence/action.yml` | `d1edc571770db90341c671b63287d958d2dfc093fc0ba7cd64937eb190396654` |
| `.github/workflows/weekly-pg-integration.yml` | `2ad9727274f6fe0e34e1d56c188d2ad7fa6a2f2e49e3c0cdcb22b5a53edaf86e` |
| `tests/unit/test_mise_tasks.py` | `3872d8f26e6c28d8df2489dab6fa41f425d8d4285fd536895103d10740097f95` |
| `tests/unit/tools/test_ci_scope.py` | `6ff7326e5371f1972160069102363d7f38f98023857145ae4b5cf1068db6370e` |
| `tests/unit/tools/test_run_observer_session.py` | `6eac5e94ab3b3208e9fb777e79f3a7b62d83c22cd91d599c6120eb865774683b` |
| `tools/run_observer_session.py` | `305f74530ea573eea2c1a37e70e44a044160479e75de0f78809f7ed57c46ac96` |
| `tools/run_rust_postgres.sh` | `a7c194377cc4ee70a4859ee46029d21d19a4b2bfadccd26abf7de9b0e91116f4` |

After qualification, comments alone changed in `tools/run_rust_postgres.sh`
to address the ShellCheck hook. Its post-qualification SHA-256 is
`4b2311bdb81400cbc9a634e9112efe666e5df013286df4aad60f369d0db2d20e`.
