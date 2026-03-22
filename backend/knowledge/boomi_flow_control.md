# Boomi Flow Control shape (reviewer knowledge)

This project’s **PERF004** rule distinguishes:

1. **Document routing / parallel processing** — the usual Flow Control step: threads, processes, “run each document individually”, batches, chunk/thread modes (`chunkStyle`, `forEachCount`, etc.). These are **not** modeled as unbounded “for” loops in AtomSphere.
2. **Loop-style configuration** — when the export includes **`loopType`** (e.g. count-based retry) **without** a maximum iteration guard, PERF004 may still report a risk.

## Official Boomi documentation

- [Flow Control step](https://help.boomi.com/docs/atomsphere/integration/process%20building/r-atm-flow_control_shape_91fdf4a1-c765-4d4b-a0c0-c8159222ee32/) — parallel processing (threads/processes), batch options (no batching, each document individually, batches of N).
- [Flow Control step and fiber executions](https://help.boomi.com/docs/atomsphere/integration/process%20building/c-atm-flow_control_shape_and_fiber_executions_b03b9567-f7b2-4f43-9c34-b96904744287/) — fibers after Flow Control with parallel options.
- [Example: Run each document individually](https://help.boomi.com/docs/atomsphere/integration/process%20building/c-atm-flow_control_shape_ex_run_each_document_individuall_5a1b8e96-d153-4cb3-b925-67d70eb25390/).

## Implementation note

Rule logic lives in `backend/rules/performance/rule_unbounded_loops.py`.
