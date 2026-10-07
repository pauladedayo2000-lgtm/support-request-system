# Customer Support Request System

A command-line Python program that receives, organises and processes customer support requests. It uses only the Python standard library, so there is nothing to install besides Python itself.

## Features

- Add a new support request
- Store customer information in dictionaries
- Block duplicate request IDs with a set
- Process requests in the order received with a queue
- Mark urgent requests as high priority
- Undo the most recent update with a stack
- Search by request ID or customer name
- Sort by date, priority or status
- Display replies and follow-ups in order with recursion
- Compare two searching approaches and two sorting approaches

## Setup

You need Python 3.9 or newer.

1. Check your version: `py --version` (Windows) or `python3 --version` (macOS and Linux).
2. Clone the repository:
   ```
   git clone https://github.com/YOUR-USERNAME/support-request-system.git
   cd support-request-system
   ```

## Run the program

```
py support_system.py
```

On macOS or Linux, use `python3 support_system.py`. You can also open `support_system.py` in IDLE and press F5.

A numbered menu appears. Type a number and press Enter. Quick start:

1. Choose `14` to load the sample data from `sample_requests.json`.
2. Choose `8` and type `priority` to see urgent requests first.
3. Choose `2` to process the oldest request, then `5` to undo it.
4. Choose `10` and type `R001` to see a reply thread printed with indentation.
5. Choose `11` to run the speed comparison.

Request IDs are labels you invent, such as `R1`. They are case sensitive.

## Run the tests

```
py -m unittest -v
```

32 tests cover adding, duplicates, queue order, priority, undo, both searches, all three sorts, both sorting methods agreeing, nested replies and the sample data loader.

## Project files

| File | Purpose |
|---|---|
| `support_system.py` | The program and menu |
| `sample_requests.json` | 8 sample requests, including nested replies |
| `test_support_system.py` | Automated tests |
| `README.md` | This file |

## Data structures used

| Feature | Structure | Why it was chosen |
|---|---|---|
| Request and customer details | Dictionary (a nested `customer` dictionary inside each request) | Named fields such as `status` and `priority` are easy to read and update |
| All requests, looked up by ID | Dictionary keyed by request ID | Finding a request by ID takes O(1) average time |
| Duplicate ID prevention | Set | Checking whether an ID exists takes O(1) average time, and a set holds each value once |
| Processing in order received | Queue (`collections.deque`) | First in, first out. `append` and `popleft` are both O(1). A plain list is O(n) for `pop(0)` |
| Undo | Stack (a list with `append` and `pop`) | The last update made is the first one reversed |
| Urgent flag | `priority` field with a keyword check | Messages containing "urgent", "asap", "emergency" or "immediately" are marked high automatically, and you can also mark one by hand |
| Replies and follow-ups | Nested lists inside dictionaries, read with recursion | A reply can have its own replies, so the depth is not known in advance and recursion follows it naturally |
| Sorting | Python list sorted by a key function | One function handles date, priority and status |

## Searching and sorting comparison

**Sorting: built-in `sorted()` against insertion sort**

| Requests | `sorted()` (Timsort) | Insertion sort |
|---|---|---|
| 500 | 0.00009 s | 0.00668 s |
| 1,000 | 0.00019 s | 0.02917 s |
| 2,000 | 0.00048 s | 0.13667 s |

Timsort runs in O(n log n). Insertion sort runs in O(n²), so doubling the list roughly quadruples its time. At 2,000 requests insertion sort was about 280 times slower. Insertion sort is only reasonable for very small lists, or lists that are already nearly sorted.

**Searching by name: linear scan against binary search (200 lookups)**

| Requests | Linear scan | Binary search | One-time index build |
|---|---|---|---|
| 1,000 | 0.0199 s | 0.0006 s | 0.0004 s |
| 5,000 | 0.1278 s | 0.0032 s | 0.0033 s |
| 20,000 | 0.5425 s | 0.0108 s | 0.0178 s |

Linear scan checks every request, O(n). Binary search needs a sorted name index, which costs O(n log n) to build, then finds a match in O(log n + k) where k is the number of matches. Binary search wins when you search often. Linear scan wins when the list is small or changes constantly, because you would have to rebuild the index after each add.

These numbers come from one run on one machine. Run menu option `11` to get your own.

## Time and space complexity

n is the number of requests and m is the number of replies.

| Operation | Time | Extra space |
|---|---|---|
| Add request | O(1) average | O(1) |
| Duplicate check | O(1) average | O(n) for the set |
| Process next request | O(1) | O(1) |
| Mark urgent, update status | O(1) | O(1) per undo entry |
| Undo | O(1), or O(m) when undoing a reply | O(n) for the stack |
| Search by ID | O(1) average | O(1) |
| Name search, linear | O(n) | O(1) |
| Name search, binary | O(log n + k) | O(n) for the index |
| Sort, `sorted()` | O(n log n) | O(n) |
| Sort, insertion | O(n²) worst case | O(1) |
| Display replies | O(m) | O(d) call stack, d = reply depth |

## Limitations and possible improvements

**Limitations**

- Data lives in memory only. Closing the program loses everything.
- Request IDs are typed by hand, so users can mistype them.
- Name search is not tolerant of typos, and binary search matches only the start of a name.
- The name index is rebuilt each time you choose binary search.
- Queue order is strictly first in, first out. A high priority request does not jump ahead.
- Manually changing a status does not remove the request from the queue.
- Urgent detection relies on four keywords and can miss or wrongly flag messages.
- Input is not validated for email format or empty fields.
- There is no user login or permission system.

**Possible improvements**

- Save and load requests with JSON or SQLite so data survives a restart.
- Generate request IDs automatically.
- Replace the queue with a priority queue (`heapq`) so urgent requests are handled first, while keeping arrival order inside each priority.
- Keep the name index up to date as requests are added.
- Add validation for emails and empty fields.
- Add a web or GUI front end.
- Add a multi-level undo and redo.
