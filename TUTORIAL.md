# Why did we move twice?

Imagine a sender who sees a plan and a receiver who can move a token. The action is relative: **move one tile east**. Repeating it changes the outcome.

## 1. Separate intent, delivery, and acknowledgment

The sender says `1 | move one tile east`. The receiver hears it, moves once, and replies `ack 1`. If that reply is lost, the sender cannot know whether the instruction was lost or the acknowledgment was lost.

`examples/missing-ack.json` stops at this uncertainty. Run it:

```sh
python trace_lab.py examples/missing-ack.json
```

The applied-action list contains `select triangle`, but the status is `incomplete`. A receiver having acted is different from the sender knowing it acted.

## 2. Retry the message, not a new intention

After waiting, the sender repeats `1 | move one tile east`. The receiver sees ID 1 in its history, does not move again, and sends another `ack 1`.

Run `examples/lost-ack.json`. Its six events are send, deliver, timeout, send, deliver, ack. Both deliveries refer to ID 1, so only one action is applied.

Now inspect `examples/id-conflict.json`. Changing the retry to `1 | move one tile west` is rejected. If one ID could mean two actions, the receiver's memory would no longer identify the intended effect.

Exercise: copy `lost-ack.json` and add another timeout/send/deliver group before the final acknowledgment. The applied-action list should still contain one move.

## 3. An old acknowledgment must not unlock a new action

In `examples/duplicate-and-stale.json`, the first instruction is complete and message 2 has started. A delayed copy of message 1 arrives, followed by `ack 1`.

The receiver ignores the duplicate action. The sender ignores the stale acknowledgment because it is waiting for **2**, not **1**. Message 2 remains pending until `ack 2` arrives.

Exercise: remove the last two events from that file. The checker should report that ID 2 is still pending. It should show only the first action as applied.

## 4. One outstanding message makes recovery understandable

`examples/out-of-order.json` tries to send ID 2 while ID 1 is still pending. The checker rejects that send, then rejects a delivery for the message it never accepted.

Pipelined protocols can support multiple outstanding messages, but they need more state and different rules. This lab deliberately uses one outstanding message so a pair of learners can explain every transition.

Exercise: repair the file by delivering and acknowledging ID 1 before sending ID 2. Finish by delivering and acknowledging ID 2. The result should contain two applied actions and exit successfully.

## 5. Try it with a partner

Use paper tokens and a small grid; no particular game is required. Agree on a sender, a receiver, message IDs, a clear acknowledgment phrase, and when to retry. A third person can keep the event log and deliberately omit one acknowledgment. The receiver must keep a written list of applied IDs.

Compare the human log with the checker. Discuss these questions:

- Did the receiver hear a whole frame before acting?
- Was a repeated ID treated as the same intention?
- Was the retry unchanged?
- Did the sender wait for the correct acknowledgment?

Do not use this exercise to claim a real system guarantees exactly-once execution. If a receiver loses its memory or participants restart numbering, a delayed duplicate may look new. Session IDs, persistence, and recovery after failure are separate lessons outside this small model.
