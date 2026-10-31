# Co-op Message Trace Lab

A small, offline tutorial for diagnosing repeated or missing instructions in a two-person puzzle. Run a JSON conversation through a checker and see why a lost acknowledgment should cause a **retry of the same message**, rather than a second action.

Python 3.10 or newer. No packages, account, network access, game installation, or telemetry. The examples are invented practice situations, not solutions from a game.

## Try the lost-acknowledgment case

Download this repository, open its directory, and run:

```sh
python trace_lab.py examples/lost-ack.json
python -m unittest -v
```

On systems where the Python command is `python3`, substitute that name. The first command ends with:

```text
Applied actions: [{"id": 1, "action": "move one tile east"}]
Status: complete
```

The message was delivered twice. The receiver moved only once. This is the difference between repeating a message and repeating its effect.

## The protocol in four rules

1. Agree on a frame: a message ID and an action, such as `1 | move one tile east`. The whole frame must be recognizable before acting.
2. Send only one new message at a time. Keep its ID and action until the matching acknowledgment arrives.
3. On a timeout, retry that **same** ID and action. The receiver remembers IDs already applied, ignores duplicates, and acknowledges them again.
4. Advance to the next ID only after the matching acknowledgment arrives. An old acknowledgment does not release a newer message.

This is a teaching model of stop-and-wait communication, not a networking implementation. The sender and receiver states are combined into one observer's event log so failures are visible. Real participants need a shared way to represent IDs and acknowledgments; the script does not decode speech, flashes, taps, or game input.

Read the [worked tutorial](TUTORIAL.md) before designing your own log.

## Explore the failures

| File | What you learn | Expected result / exit |
| --- | --- | --- |
| `examples/normal.json` | Two instructions, each acknowledged before the next | complete / 0 |
| `examples/lost-ack.json` | Retry after an acknowledgment goes missing | complete / 0 |
| `examples/duplicate-and-stale.json` | Duplicate delivery and an old acknowledgment during a newer message | complete / 0 |
| `examples/out-of-order.json` | Sending a second instruction too early | invalid / 1 |
| `examples/id-conflict.json` | Reusing an ID with a different action | invalid / 1 |
| `examples/missing-ack.json` | The receiver acted, but the sender still cannot advance | incomplete / 1 |

Exit 2 means the file or event format could not be read. Failed examples are intentional. Add `--json` for structured diagnostics. Rejected events do not change the model's state; later diagnostics describe the remaining accepted prefix and subsequent valid events, not a repaired real conversation.

## Event format

```json
[
  {"event": "send", "id": 1, "action": "select triangle"},
  {"event": "deliver", "id": 1, "action": "select triangle"},
  {"event": "ack", "id": 1}
]
```

- `send`: the sender emits a complete frame. New IDs start at 1 and increase by one. A retry requires a recorded `timeout`.
- `deliver`: that frame reaches the receiver, which applies a new action once or ignores an already applied ID.
- `ack`: an acknowledgment reaches the sender. It is not merely the receiver attempting to send one.
- `timeout`: the sender's agreed waiting period expires. No duration is prescribed by this model.

A lost message has no `deliver` event; a lost acknowledgment has no `ack` event. The log must be a nonempty array of at most 10,000 events. IDs are positive integers; actions contain 1–256 characters, must not be whitespace-only, and match exactly, including case and spaces. Extra keys are rejected to catch misspellings.

## Limits and attribution

The model assumes intact frames, known participants, an accurate observer, and receiver memory that lasts for the entire trace. It does not model a receiver restart, a new session, simultaneous senders, corrupted IDs, malicious messages, or a human forgetting an action. It cannot guarantee exactly-once behavior outside its simulated log. Do not reset IDs or forget the receiver history partway through a real exercise.

This repository was prepared for Big Walk Guide, an unofficial fan resource, with AI-assisted implementation and review. Its original examples extend the communication-planning topic discussed in the [Big Walk signal-planning guide](https://thebigwalk.world/en/protocols). That page is optional background; this tutorial and checker work independently. Neither project is affiliated with the game's developer or publisher, and this is not a game mod, an integration, or a tested in-game strategy.

Code, prose, and example traces are original material released under the [MIT License](LICENSE). No game assets or third-party code are included.
