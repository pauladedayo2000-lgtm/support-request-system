"""Automated tests. Run with:  py -m unittest -v"""

import io
import os
import unittest
from contextlib import redirect_stdout

from support_system import SupportSystem, insertion_sort

SAMPLE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "sample_requests.json")


def make_system():
    s = SupportSystem()
    s.add_request("R1", "Ada Okoro", "a@x.com", "Hello", date="2026-01-03 10:00:00")
    s.add_request("R2", "Bayo Bello", "b@x.com", "Server down, urgent",
                  date="2026-01-01 10:00:00")
    s.add_request("R3", "Ada Eze", "c@x.com", "Question", date="2026-01-02 10:00:00")
    return s


class TestAddAndDuplicates(unittest.TestCase):
    def test_add_stores_customer_dictionary(self):
        s = make_system()
        self.assertEqual(s.requests["R1"]["customer"],
                         {"name": "Ada Okoro", "email": "a@x.com"})

    def test_duplicate_id_is_rejected(self):
        s = make_system()
        ok, _ = s.add_request("R1", "Someone", "s@x.com", "Again")
        self.assertFalse(ok)
        self.assertEqual(len(s.requests), 3)
        self.assertEqual(len(s.queue), 3)


class TestQueue(unittest.TestCase):
    def test_processes_in_order_received(self):
        s = make_system()
        order = [s.process_next()["id"] for _ in range(3)]
        self.assertEqual(order, ["R1", "R2", "R3"])

    def test_empty_queue_returns_none(self):
        self.assertIsNone(SupportSystem().process_next())

    def test_processing_sets_status(self):
        s = make_system()
        self.assertEqual(s.process_next()["status"], "in progress")


class TestPriority(unittest.TestCase):
    def test_keyword_sets_high_priority(self):
        s = make_system()
        self.assertEqual(s.requests["R2"]["priority"], "high")
        self.assertEqual(s.requests["R1"]["priority"], "normal")

    def test_urgent_flag_sets_high_priority(self):
        s = SupportSystem()
        s.add_request("R9", "Z", "z@x.com", "Plain message", urgent=True)
        self.assertEqual(s.requests["R9"]["priority"], "high")

    def test_mark_urgent(self):
        s = make_system()
        s.mark_urgent("R1")
        self.assertEqual(s.requests["R1"]["priority"], "high")

    def test_mark_urgent_unknown_id(self):
        ok, _ = make_system().mark_urgent("NOPE")
        self.assertFalse(ok)


class TestUndo(unittest.TestCase):
    def test_undo_add(self):
        s = make_system()
        s.undo()
        self.assertNotIn("R3", s.requests)
        self.assertNotIn("R3", s.ids)
        self.assertEqual(list(s.queue), ["R1", "R2"])

    def test_undo_add_then_id_can_be_reused(self):
        s = make_system()
        s.undo()
        ok, _ = s.add_request("R3", "New", "n@x.com", "Reused ID")
        self.assertTrue(ok)

    def test_undo_priority(self):
        s = make_system()
        s.mark_urgent("R1")
        s.undo()
        self.assertEqual(s.requests["R1"]["priority"], "normal")

    def test_undo_status(self):
        s = make_system()
        s.update_status("R1", "resolved")
        s.undo()
        self.assertEqual(s.requests["R1"]["status"], "open")

    def test_undo_process_returns_request_to_front(self):
        s = make_system()
        s.process_next()
        s.undo()
        self.assertEqual(list(s.queue), ["R1", "R2", "R3"])
        self.assertEqual(s.requests["R1"]["status"], "open")

    def test_undo_only_reverses_most_recent(self):
        s = make_system()
        s.mark_urgent("R1")
        s.update_status("R1", "resolved")
        s.undo()
        self.assertEqual(s.requests["R1"]["status"], "open")
        self.assertEqual(s.requests["R1"]["priority"], "high")

    def test_undo_with_empty_stack(self):
        ok, _ = SupportSystem().undo()
        self.assertFalse(ok)


class TestSearch(unittest.TestCase):
    def test_search_by_id(self):
        s = make_system()
        self.assertEqual(s.search_by_id("R2")["customer"]["name"], "Bayo Bello")
        self.assertIsNone(s.search_by_id("NOPE"))

    def test_linear_name_search(self):
        s = make_system()
        ids = sorted(r["id"] for r in s.linear_search_name("ada"))
        self.assertEqual(ids, ["R1", "R3"])

    def test_binary_name_search_matches_linear(self):
        s = make_system()
        index = s.build_name_index()
        binary = sorted(r["id"] for r in s.binary_search_name(index, "ada"))
        linear = sorted(r["id"] for r in s.linear_search_name("ada"))
        self.assertEqual(binary, linear)

    def test_binary_search_no_match(self):
        s = make_system()
        self.assertEqual(s.binary_search_name(s.build_name_index(), "zzz"), [])


class TestSort(unittest.TestCase):
    def ids(self, items):
        return [r["id"] for r in items]

    def test_sort_by_date(self):
        self.assertEqual(self.ids(make_system().sort_requests("date")),
                         ["R2", "R3", "R1"])

    def test_sort_by_priority_high_first(self):
        result = make_system().sort_requests("priority")
        self.assertEqual(result[0]["id"], "R2")

    def test_sort_by_status(self):
        s = make_system()
        s.update_status("R1", "resolved")
        s.update_status("R2", "in progress")
        self.assertEqual(self.ids(s.sort_requests("status")), ["R3", "R2", "R1"])

    def test_both_sorting_methods_agree(self):
        s = make_system()
        for field in ("date", "priority", "status"):
            self.assertEqual(self.ids(s.sort_requests(field, "builtin")),
                             self.ids(s.sort_requests(field, "insertion")))

    def test_insertion_sort_basic(self):
        self.assertEqual(insertion_sort([3, 1, 2], key=lambda x: x), [1, 2, 3])

    def test_invalid_sort_field(self):
        with self.assertRaises(ValueError):
            make_system().sort_requests("colour")


class TestRepliesRecursion(unittest.TestCase):
    def test_nested_replies_display_in_order(self):
        s = make_system()
        s.add_reply("R1", "First")
        s.add_reply("R1", "Child", 1)
        s.add_reply("R1", "Grandchild", 2)
        s.add_reply("R1", "Second")
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            s.display_replies(s.requests["R1"]["replies"])
        lines = buffer.getvalue().splitlines()
        self.assertEqual(lines, ["[1] First", "    [2] Child",
                                 "        [3] Grandchild", "[4] Second"])

    def test_reply_to_missing_parent(self):
        s = make_system()
        ok, _ = s.add_reply("R1", "Orphan", 99)
        self.assertFalse(ok)

    def test_undo_reply(self):
        s = make_system()
        s.add_reply("R1", "First")
        s.undo()
        self.assertEqual(s.requests["R1"]["replies"], [])


class TestSampleData(unittest.TestCase):
    def test_sample_file_loads(self):
        s = SupportSystem()
        added, skipped = s.load_from_file(SAMPLE)
        self.assertEqual((added, skipped), (8, 0))
        self.assertEqual(s.undo_stack, [])

    def test_loading_twice_skips_duplicates(self):
        s = SupportSystem()
        s.load_from_file(SAMPLE)
        added, skipped = s.load_from_file(SAMPLE)
        self.assertEqual((added, skipped), (0, 8))

    def test_sample_replies_are_nested(self):
        s = SupportSystem()
        s.load_from_file(SAMPLE)
        first = s.requests["R001"]["replies"][0]
        self.assertEqual(first["replies"][0]["replies"][0]["text"],
                         "Will do. A technician arrives by 3 pm.")


if __name__ == "__main__":
    unittest.main()
