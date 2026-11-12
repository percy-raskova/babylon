# Native measurement method: bounded research, 9 November 2026

This note supports ADR294. Source guidance, one Babylon diagnostic and the
Director's Designed method are distinct evidence.

## Primary guidance

[Bevy profiling guide](https://github.com/bevyengine/bevy/blob/main/docs/profiling.md):
profiling changes execution, and allocation profiling adds overhead. Its
command-line capture advice avoids a competing live graphical `profiler`.
This does not measure Babylon's exact overhead or justify a build change.

[Rust Performance Book: benchmarking](https://nnethercote.github.io/perf-book/benchmarking.html):
compare the same work. Wall time describes user experience but varies.
One serial pair does not prove a distribution or universal speedup.

[Rust Performance Book: profiling](https://nnethercote.github.io/perf-book/profiling.html):
debug information helps profile optimized code, and sampling can find
`hotspots`. Existing Babylon build controls remain authoritative.

[tracing level filters](https://docs.rs/tracing/latest/tracing/level_filters/index.html)
can omit disabled instrumentation at compile time.
[Span guidance](https://docs.rs/tracing/latest/tracing/span/struct.Span.html)
cautions against entered span guards across asynchronous waits. This
investigation diagnosed no such Babylon span defect.

Charity Majors' [structured events essay](https://charity.wtf/p/live-your-best-life-with-structured-events)
and Honeycomb's [observability manifesto](https://www.honeycomb.io/blog/observability-a-manifesto)
favor retaining raw structured events and context for later questions.
These primary essays are separate from the unavailable book.

The bounded local shelf search covered filenames, PDF Title/Author fields,
three EPUB package metadata records and cryptic PDF/ZIP metadata under
`/home/user/Downloads/babylon_books`, plus adjacent shelves. It found no
identifiable copy of *Observability Engineering*. The investigation read no
book text and offers no chapter or page advice. The October 26 briefing
[remains historical](33-observability-canon-for-qualification-and-intel.md).

## Babylon observation and decision

**Observed:** one serial same-build diagnostic opened in 130.587161622 seconds
without capture. The captured counterpart reached the 180-second limit with
at least 41.718759413 seconds of imposed freezes. Retained P0 semantics matched.
Order and cache conditions can vary. This pair establishes neither historical
sole cause, a timing distribution nor native qualification. Keep raw evidence
and never subtract freezes to manufacture a passing duration.

**Derived application:** keep mode, source/build, input, workload, step and
identity context alongside raw measurements before deriving summaries.
Existing production-projection timings nest parent and child wall scopes.
Adding them would double count elapsed work.

**Designed:** the Director approved separate ordinary timing and complete memory
members, with both required by ADR294. Keep the same build, captured inputs and
actual decision semantics. Preserve independent command/receipt/marker and
restore/retirement custody. This delivery adds no telemetry backend, dependency,
`profiler` installation, tracing refactor or build-profile change. Actual native
qualification and human acceptance need their own evidence.
