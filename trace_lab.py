"""Check a small stop-and-wait message log. Python 3.10+, standard library only."""

import argparse
import json
from pathlib import Path
import sys


def validate_events(events):
    if not isinstance(events, list) or not events:
        raise ValueError("trace must be a nonempty JSON array")
    if len(events) > 10000:
        raise ValueError("trace is limited to 10000 events")
    for index, event in enumerate(events, 1):
        if not isinstance(event, dict):
            raise ValueError(f"event {index}: expected an object")
        kind = event.get("event")
        if not isinstance(kind, str) or kind not in {"send", "deliver", "ack", "timeout"}:
            raise ValueError(f"event {index}: event must be send, deliver, ack, or timeout")
        keys = {"event", "id", "action"} if kind in {"send", "deliver"} else {"event", "id"}
        if set(event) != keys:
            raise ValueError(f"event {index}: expected keys {', '.join(sorted(keys))}")
        if type(event["id"]) is not int or event["id"] < 1:
            raise ValueError(f"event {index}: id must be a positive integer")
        if "action" in event:
            action = event["action"]
            if not isinstance(action, str) or not action.strip() or len(action) > 256:
                raise ValueError(f"event {index}: action must contain 1 to 256 characters")


def check_trace(events):
    """Return diagnostics; rejected events never change the simulated state."""
    validate_events(events)
    sent = {}
    applied = {}
    pending = None
    timed_out = False
    steps = []
    errors = []

    for index, event in enumerate(events, 1):
        kind = event["event"]
        seq = event["id"]
        action = event.get("action")
        error = None
        message = ""

        if kind == "send":
            if seq in sent and action != sent[seq]:
                error = "ID reused with different action; a retry must keep both unchanged"
            elif pending is not None:
                if seq != pending:
                    error = f"message {pending} is still pending; wait for its acknowledgment"
                elif not timed_out:
                    error = "retry before timeout; record the wait before retrying"
                else:
                    timed_out = False
                    message = "retry sent with the same ID and action"
            elif seq != len(sent) + 1:
                error = f"next new message must have ID {len(sent) + 1}"
            else:
                sent[seq] = action
                pending = seq
                timed_out = False
                message = "new message sent; wait for acknowledgment"

        elif kind == "deliver":
            if seq not in sent:
                error = "delivery has no earlier accepted send"
            elif action != sent[seq]:
                error = "delivered action differs from the sent action"
            elif seq in applied:
                message = "duplicate delivery ignored; receiver should acknowledge again"
            elif seq != len(applied) + 1:
                error = f"receiver expects ID {len(applied) + 1}"
            else:
                applied[seq] = action
                message = "action applied once; receiver should acknowledge this ID"

        elif kind == "ack":
            if seq not in applied:
                error = "acknowledgment before the action was received"
            elif seq != pending:
                message = "stale acknowledgment ignored; current pending message unchanged"
            else:
                pending = None
                timed_out = False
                message = "acknowledgment arrived; next new message is allowed"

        elif pending != seq:
            error = "timeout does not match a pending message"
        else:
            timed_out = True
            message = "wait expired; retry the same ID and action, or keep waiting"

        if error:
            errors.append({"step": index, "message": error})
            message = "REJECTED: " + error
        steps.append({"step": index, "event": kind, "id": seq, "message": message})

    if errors:
        status = "invalid"
    elif pending is not None:
        status = "incomplete"
    else:
        status = "complete"
    return {"status": status, "steps": steps, "errors": errors, "pending": pending,
            "applied": [{"id": seq, "action": action} for seq, action in applied.items()]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path, help="JSON event log")
    parser.add_argument("--json", action="store_true", help="print machine-readable diagnostics")
    args = parser.parse_args(argv)
    try:
        events = json.loads(args.trace.read_text(encoding="utf-8"))
        result = check_trace(events)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        for step in result["steps"]:
            print(f"{step['step']:02d} {step['event']} #{step['id']}: {step['message']}")
        print("Applied actions:", json.dumps(result["applied"], ensure_ascii=True))
        print("Status:", result["status"])
        if result["pending"] is not None:
            print("Still waiting for acknowledgment:", result["pending"])
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
