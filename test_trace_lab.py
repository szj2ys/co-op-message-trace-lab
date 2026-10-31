import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from trace_lab import check_trace


ROOT = Path(__file__).parent


def example(name):
    return json.loads((ROOT / "examples" / (name + ".json")).read_text(encoding="utf-8"))


class TraceTests(unittest.TestCase):
    def test_normal_sequence_applies_both_actions_in_order(self):
        result = check_trace(example("normal"))
        self.assertEqual(result["status"], "complete")
        self.assertEqual([item["action"] for item in result["applied"]],
                         ["select triangle", "move one tile east"])

    def test_lost_ack_does_not_repeat_a_relative_move(self):
        result = check_trace(example("lost-ack"))
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["applied"], [{"id": 1, "action": "move one tile east"}])

    def test_stale_ack_cannot_release_the_next_message(self):
        events = example("duplicate-and-stale")
        partial = check_trace(events[:6])
        self.assertEqual(partial["pending"], 2)
        self.assertEqual(len(partial["applied"]), 1)
        self.assertEqual(check_trace(events)["status"], "complete")

    def test_conflicting_retry_cannot_change_receiver_action(self):
        result = check_trace(example("id-conflict"))
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["applied"], [{"id": 1, "action": "move one tile east"}])
        self.assertEqual(result["pending"], 1)

    def test_out_of_order_send_does_not_create_deliverable_message(self):
        result = check_trace(example("out-of-order"))
        self.assertEqual(len(result["errors"]), 2)
        self.assertEqual(result["applied"], [])
        self.assertEqual(result["pending"], 1)

    def test_ack_before_delivery_is_rejected(self):
        result = check_trace([{"event": "send", "id": 1, "action": "select triangle"},
                              {"event": "ack", "id": 1}])
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["pending"], 1)

    def test_repeated_loss_keeps_action_exactly_once_in_this_trace(self):
        events = example("lost-ack")[:-1]
        for _ in range(20):
            events += [{"event": "timeout", "id": 1},
                       {"event": "send", "id": 1, "action": "move one tile east"},
                       {"event": "deliver", "id": 1, "action": "move one tile east"}]
        events.append({"event": "ack", "id": 1})
        result = check_trace(events)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(result["applied"]), 1)

    def test_bad_event_shapes_raise_input_errors(self):
        invalid = [[], {}, [None], [{"event": [], "id": 1}],
                   [{"event": "ack", "id": True}], [{"event": "ack", "id": 0}],
                   [{"event": "send", "id": 1, "action": " "}],
                   [{"event": "send", "id": 1, "action": "x" * 257}],
                   [{"event": "ack", "id": 1, "typo": 1}]]
        for events in invalid:
            with self.subTest(events=events), self.assertRaises(ValueError):
                check_trace(events)

    def test_cli_exit_codes_and_json_output(self):
        for name, code, status in [("normal", 0, "complete"),
                                   ("lost-ack", 0, "complete"),
                                   ("duplicate-and-stale", 0, "complete"),
                                   ("out-of-order", 1, "invalid"),
                                   ("id-conflict", 1, "invalid"),
                                   ("missing-ack", 1, "incomplete")]:
            with self.subTest(name=name):
                process = subprocess.run([sys.executable, str(ROOT / "trace_lab.py"),
                                          str(ROOT / "examples" / (name + ".json")), "--json"],
                                         capture_output=True, text=True)
                self.assertEqual(process.returncode, code, process.stderr)
                self.assertEqual(json.loads(process.stdout)["status"], status)

    def test_malformed_json_is_a_cli_input_error_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "bad.json"
            trace.write_text("[", encoding="utf-8")
            process = subprocess.run([sys.executable, str(ROOT / "trace_lab.py"), str(trace)],
                                     capture_output=True, text=True)
        self.assertEqual(process.returncode, 2)
        self.assertIn("Input error:", process.stderr)
        self.assertNotIn("Traceback", process.stderr)


if __name__ == "__main__":
    unittest.main()
