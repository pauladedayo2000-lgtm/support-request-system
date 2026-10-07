"""
Customer Support Request System
Run in IDLE: File > Open, then press F5.
"""

from collections import deque
from datetime import datetime
import json
import os
import random
import time

PRIORITY_RANK = {"high": 0, "normal": 1}
STATUS_RANK = {"open": 0, "in progress": 1, "resolved": 2}
URGENT_WORDS = ("urgent", "asap", "emergency", "immediately")


class SupportSystem:
    def __init__(self):
        self.requests = {}        # dict: request_id -> request dict
        self.ids = set()          # set: blocks duplicate request IDs
        self.queue = deque()      # queue: request IDs in the order received
        self.undo_stack = []      # stack: most recent update on top
        self.next_reply_id = 1

    # ------------------------------------------------------------------
    # Add and update
    # ------------------------------------------------------------------
    def add_request(self, request_id, name, email, message,
                    urgent=False, date=None):
        if request_id in self.ids:                     # set lookup, O(1)
            return False, f"Request ID {request_id} already exists."

        text = message.lower()
        if urgent or any(word in text for word in URGENT_WORDS):
            priority = "high"
        else:
            priority = "normal"

        self.requests[request_id] = {
            "id": request_id,
            "customer": {"name": name, "email": email},   # dict of customer info
            "message": message,
            "date": date or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "priority": priority,
            "status": "open",
            "replies": [],     # list of reply nodes; each node has its own "replies"
        }
        self.ids.add(request_id)
        self.queue.append(request_id)                  # enqueue, O(1)
        self.undo_stack.append(("add", request_id))    # push, O(1)
        return True, f"Added {request_id} with {priority} priority."

    def mark_urgent(self, request_id):
        req = self.requests.get(request_id)
        if req is None:
            return False, "Request not found."
        self.undo_stack.append(("priority", request_id, req["priority"]))
        req["priority"] = "high"
        return True, f"{request_id} is now high priority."

    def update_status(self, request_id, status):
        req = self.requests.get(request_id)
        if req is None:
            return False, "Request not found."
        if status not in STATUS_RANK:
            return False, "Status must be: open, in progress, or resolved."
        self.undo_stack.append(("status", request_id, req["status"]))
        req["status"] = status
        return True, f"{request_id} status set to {status}."

    def process_next(self):
        """Take the oldest request off the queue (first in, first out)."""
        if not self.queue:
            return None
        request_id = self.queue.popleft()              # dequeue, O(1)
        req = self.requests[request_id]
        self.undo_stack.append(("process", request_id, req["status"]))
        req["status"] = "in progress"
        return req

    # ------------------------------------------------------------------
    # Sample data
    # ------------------------------------------------------------------
    def load_from_file(self, path):
        """Load requests (and nested replies) from a JSON file.
        Returns (added, skipped). Duplicate IDs are skipped."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        added = skipped = 0
        for item in data:
            ok, _ = self.add_request(item["id"], item["name"], item["email"],
                                     item["message"], item.get("urgent", False),
                                     item.get("date"))
            if ok:
                added += 1
                self._load_replies(item["id"], item.get("replies", []), None)
            else:
                skipped += 1
        self.undo_stack.clear()   # loading data is not an undoable update
        return added, skipped

    def _load_replies(self, request_id, replies, parent_id):
        for reply in replies:
            self.add_reply(request_id, reply["text"], parent_id)
            new_id = self.next_reply_id - 1
            self._load_replies(request_id, reply.get("replies", []), new_id)  # recursion

    # ------------------------------------------------------------------
    # Replies (recursion)
    # ------------------------------------------------------------------
    def add_reply(self, request_id, text, parent_reply_id=None):
        req = self.requests.get(request_id)
        if req is None:
            return False, "Request not found."
        node = {"reply_id": self.next_reply_id, "text": text, "replies": []}
        if parent_reply_id is None:
            req["replies"].append(node)
        else:
            parent = self._find_reply(req["replies"], parent_reply_id)
            if parent is None:
                return False, "Parent reply not found."
            parent["replies"].append(node)
        self.undo_stack.append(("reply", request_id, node["reply_id"]))
        self.next_reply_id += 1
        return True, f"Reply {node['reply_id']} added."

    def _find_reply(self, replies, reply_id):
        for node in replies:
            if node["reply_id"] == reply_id:
                return node
            found = self._find_reply(node["replies"], reply_id)   # recursion
            if found:
                return found
        return None

    def _remove_reply(self, replies, reply_id):
        for i, node in enumerate(replies):
            if node["reply_id"] == reply_id:
                del replies[i]
                return True
            if self._remove_reply(node["replies"], reply_id):     # recursion
                return True
        return False

    def display_replies(self, replies, depth=0):
        """Print replies in order, indenting each follow-up level."""
        for node in replies:
            print("    " * depth + f"[{node['reply_id']}] {node['text']}")
            self.display_replies(node["replies"], depth + 1)      # recursion

    # ------------------------------------------------------------------
    # Undo
    # ------------------------------------------------------------------
    def undo(self):
        if not self.undo_stack:
            return False, "Nothing to undo."
        action = self.undo_stack.pop()                 # pop, O(1)
        kind = action[0]

        if kind == "add":
            request_id = action[1]
            del self.requests[request_id]
            self.ids.discard(request_id)
            self.queue.pop()   # the newest add is always at the right end
            return True, f"Undid adding {request_id}."
        if kind == "priority":
            self.requests[action[1]]["priority"] = action[2]
            return True, f"Restored priority on {action[1]}."
        if kind == "status":
            self.requests[action[1]]["status"] = action[2]
            return True, f"Restored status on {action[1]}."
        if kind == "process":
            self.requests[action[1]]["status"] = action[2]
            self.queue.appendleft(action[1])
            return True, f"{action[1]} is back at the front of the queue."
        if kind == "reply":
            self._remove_reply(self.requests[action[1]]["replies"], action[2])
            return True, f"Removed reply {action[2]}."
        return False, "Unknown action."

    # ------------------------------------------------------------------
    # Searching
    # ------------------------------------------------------------------
    def search_by_id(self, request_id):
        return self.requests.get(request_id)           # hash lookup, O(1)

    def linear_search_name(self, name):
        """Approach 1: scan every request. O(n) time, O(1) extra space."""
        name = name.lower()
        return [r for r in self.requests.values()
                if name in r["customer"]["name"].lower()]

    def build_name_index(self):
        """Sorted list of (lowercase name, id). O(n log n) time, O(n) space."""
        return sorted((r["customer"]["name"].lower(), r["id"])
                      for r in self.requests.values())

    def binary_search_name(self, index, prefix):
        """Approach 2: binary search on a sorted index (matches name starts).
        O(log n + k) time for k matches."""
        prefix = prefix.lower()
        low, high = 0, len(index)
        while low < high:                              # find first entry >= prefix
            mid = (low + high) // 2
            if index[mid][0] < prefix:
                low = mid + 1
            else:
                high = mid
        results = []
        while low < len(index) and index[low][0].startswith(prefix):
            results.append(self.requests[index[low][1]])
            low += 1
        return results

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------
    @staticmethod
    def sort_key(field):
        if field == "date":
            return lambda r: r["date"]
        if field == "priority":
            return lambda r: PRIORITY_RANK[r["priority"]]
        if field == "status":
            return lambda r: STATUS_RANK[r["status"]]
        raise ValueError("Sort field must be date, priority, or status.")

    def sort_requests(self, field, method="builtin"):
        items = list(self.requests.values())
        key = self.sort_key(field)
        if method == "insertion":
            return insertion_sort(items, key)
        return sorted(items, key=key)                  # Timsort, O(n log n)


def insertion_sort(items, key):
    """Approach 2: simple insertion sort. O(n^2) time, O(1) extra space, stable."""
    items = list(items)
    for i in range(1, len(items)):
        current = items[i]
        j = i - 1
        while j >= 0 and key(items[j]) > key(current):
            items[j + 1] = items[j]
            j -= 1
        items[j + 1] = current
    return items


# ----------------------------------------------------------------------
# Display helpers
# ----------------------------------------------------------------------
def show(req):
    c = req["customer"]
    print(f"{req['id']:<8} {req['date']}  {req['priority']:<7} "
          f"{req['status']:<12} {c['name']} <{c['email']}>")
    print(f"         {req['message']}")


def show_many(requests):
    if not requests:
        print("No matching requests.")
    for r in requests:
        show(r)


# ----------------------------------------------------------------------
# Benchmark: compare two searching and two sorting approaches
# ----------------------------------------------------------------------
def run_comparison():
    print("\nRunning comparison. This takes a few seconds...\n")
    first = ["Ada", "Bayo", "Chidi", "Dayo", "Emeka", "Funke", "Gbenga", "Halima"]
    last = ["Okoro", "Bello", "Adeyemi", "Musa", "Eze", "Ibrahim", "Nwosu", "Yusuf"]

    print("SORTING by date (seconds)")
    print(f"{'n':>7} {'built-in sorted':>16} {'insertion sort':>16}")
    for n in (500, 1000, 2000):
        s = SupportSystem()
        for i in range(n):
            day = random.randint(1, 28)
            s.add_request(f"R{i}", f"{random.choice(first)} {random.choice(last)}",
                          "x@mail.com", "test", date=f"2026-01-{day:02d} 10:00:00")
        t = time.perf_counter(); s.sort_requests("date"); a = time.perf_counter() - t
        t = time.perf_counter(); s.sort_requests("date", "insertion"); b = time.perf_counter() - t
        print(f"{n:>7} {a:>16.5f} {b:>16.5f}")

    print("\nSEARCHING by name prefix (seconds for 200 searches)")
    print(f"{'n':>7} {'linear scan':>16} {'binary search':>16} {'index build':>14}")
    for n in (1000, 5000, 20000):
        s = SupportSystem()
        for i in range(n):
            s.add_request(f"R{i}", f"{random.choice(first)} {random.choice(last)}",
                          "x@mail.com", "test")
        t = time.perf_counter(); index = s.build_name_index(); build = time.perf_counter() - t
        t = time.perf_counter()
        for _ in range(200):
            s.linear_search_name("Ada Okoro")
        lin = time.perf_counter() - t
        t = time.perf_counter()
        for _ in range(200):
            s.binary_search_name(index, "Ada Okoro")
        binary = time.perf_counter() - t
        print(f"{n:>7} {lin:>16.5f} {binary:>16.5f} {build:>14.5f}")

    print("\nBinary search is faster per lookup, but you pay once to build the")
    print("sorted index and you must rebuild it after adding requests.")


COMPLEXITY = """
EXPECTED TIME AND SPACE COMPLEXITY (n = number of requests)

Operation                         Time              Extra space
Add request (set + dict + queue)  O(1) average      O(1) per request
Duplicate ID check (set)          O(1) average      O(n) for the set
Process next (deque popleft)      O(1)              O(1)
Mark urgent / update status       O(1)              O(1) per undo entry
Undo (stack pop)                  O(1)*             O(n) for the stack
Search by ID (dict)               O(1) average      O(1)
Search by name, linear scan       O(n)              O(1)
Search by name, binary search     O(log n + k)      O(n) for the index
Build sorted name index           O(n log n)        O(n)
Sort with sorted() (Timsort)      O(n log n)        O(n)
Sort with insertion sort          O(n^2) worst      O(1)
Display replies (recursion)       O(m) for m replies O(d) call stack, d = depth
Add reply under a parent          O(m) to find it   O(d)

* Undoing a reply is O(m) because the reply must be found and removed.
Overall storage for the system is O(n + m).
"""


# ----------------------------------------------------------------------
# Menu
# ----------------------------------------------------------------------
MENU = """
===== SUPPORT REQUEST SYSTEM =====
 1  Add request
 2  Process next request (queue)
 3  Mark request urgent
 4  Update request status
 5  Undo last update
 6  Search by ID
 7  Search by customer name
 8  Sort and list requests
 9  Add reply or follow-up
10  Show replies for a request
11  Compare sorting and searching speed
12  Show time and space complexity
13  Show queue (order received)
14  Load sample data
 0  Exit
"""


def main():
    system = SupportSystem()
    while True:
        print(MENU)
        choice = input("Choose: ").strip()

        if choice == "1":
            rid = input("Request ID: ").strip()
            name = input("Customer name: ").strip()
            email = input("Customer email: ").strip()
            msg = input("Message: ").strip()
            urgent = input("Urgent? (y/n): ").strip().lower() == "y"
            print(system.add_request(rid, name, email, msg, urgent)[1])

        elif choice == "2":
            req = system.process_next()
            if req is None:
                print("The queue is empty.")
            else:
                print("Now processing:")
                show(req)

        elif choice == "3":
            print(system.mark_urgent(input("Request ID: ").strip())[1])

        elif choice == "4":
            rid = input("Request ID: ").strip()
            status = input("New status (open / in progress / resolved): ").strip().lower()
            print(system.update_status(rid, status)[1])

        elif choice == "5":
            print(system.undo()[1])

        elif choice == "6":
            req = system.search_by_id(input("Request ID: ").strip())
            show(req) if req else print("Not found.")

        elif choice == "7":
            name = input("Customer name (or start of it): ").strip()
            method = input("Method: 1 = linear, 2 = binary: ").strip()
            if method == "2":
                show_many(system.binary_search_name(system.build_name_index(), name))
            else:
                show_many(system.linear_search_name(name))

        elif choice == "8":
            field = input("Sort by (date / priority / status): ").strip().lower()
            try:
                show_many(system.sort_requests(field))
            except ValueError as err:
                print(err)

        elif choice == "9":
            rid = input("Request ID: ").strip()
            text = input("Reply text: ").strip()
            parent = input("Reply to which reply number? (Enter for none): ").strip()
            parent_id = int(parent) if parent.isdigit() else None
            print(system.add_reply(rid, text, parent_id)[1])

        elif choice == "10":
            req = system.search_by_id(input("Request ID: ").strip())
            if req is None:
                print("Not found.")
            elif not req["replies"]:
                print("No replies yet.")
            else:
                system.display_replies(req["replies"])

        elif choice == "11":
            run_comparison()

        elif choice == "12":
            print(COMPLEXITY)

        elif choice == "13":
            show_many([system.requests[i] for i in system.queue])

        elif choice == "14":
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "sample_requests.json")
            try:
                added, skipped = system.load_from_file(path)
                print(f"Loaded {added} requests. Skipped {skipped} duplicates.")
            except FileNotFoundError:
                print("sample_requests.json not found next to the program.")

        elif choice == "0":
            print("Goodbye.")
            break
        else:
            print("Please choose a number from the menu.")


if __name__ == "__main__":
    main()
