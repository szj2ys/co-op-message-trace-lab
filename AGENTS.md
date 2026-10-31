# Repository guidance

- Purpose: a small offline stop-and-wait communication tutorial and trace checker.
- Runtime: Python 3.10+, standard library only. Do not add a network or game dependency.
- Run: `python trace_lab.py examples/lost-ack.json`; test: `python -m unittest -v`.
- Keep the event contract and exit codes in README.md aligned with trace_lab.py.
- Examples describe invented practice situations. Do not claim game integration or real-world exactly-once guarantees.
- Current scope excludes receiver restarts, session recovery, concurrent senders, and corrupted frames.
