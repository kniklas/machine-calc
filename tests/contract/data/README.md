Golden baseline fixtures for the drilling REPL (task T013a).

`drilling_baseline_session.txt` is the byte-for-byte stdout of a complete
drilling REPL session captured from `machine_calc.cli.run()` **before** the
`009-milling-calculations` operation-selection refactor split `run()` into
per-operation session functions.

`drilling_baseline_input.txt` is the scripted stdin that produced it.

`tests/contract/test_drilling_unchanged_after_operation_prompt.py` replays
that same input — prefixed with a `drilling` operation selection — against the
refactored REPL and asserts the remaining output is identical, which is the
only way to prove the FR-002 / SC-005 "drilling is unchanged" guarantee after
the refactor.

Do not regenerate these files to make a failing test pass: a diff means
drilling behaviour actually changed.
