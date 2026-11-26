# OS Resource Management Simulator

An integrated, menu-driven Python application demonstrating CPU scheduling, page replacement, deadlock avoidance, and disk scheduling. It compares multiple algorithms using shared sample datasets and can generate a concise analysis report. Python 3.10 or newer is recommended; no third-party packages are needed.

## Run

From this folder, run `python os_simulator.py` (Windows) or `python3 os_simulator.py` (Linux/macOS). On systems with Bash, `bash run.sh` starts the same application. Select a menu item and enter `0` to exit. Choosing report generation prints the comparison and writes `report.txt`. Activity and handled errors are recorded in `activity.log`.

## Modules

- **CPU scheduling:** FCFS, non-preemptive SJF, and Round Robin (quantum 2); arrival times are honored. Reports completion, turnaround, and waiting time, plus a Gantt-style trace.
- **Memory:** FIFO, LRU, and OPT page replacement; displays hits, faults, rate, and supports per-reference frame traces in the Python result.
- **Deadlock:** Banker's safety algorithm reports whether the supplied allocation state has a safe completion order.
- **Storage:** FCFS, SSTF, SCAN, and C-SCAN disk scheduling; SCAN sweeps upward first and returns, while C-SCAN wraps from the maximum cylinder to zero.
- **Reporting/testing:** shared inputs, comparative metrics, input validation, exception handling, and timestamped activity logging.

## Input data

Edit JSON files in `data/` to try other workloads. Jobs require unique `pid` strings, non-negative integer `arrival`, and positive integer `burst` and `memory`. Page IDs and disk cylinders must be non-negative; disk requests must be within `0..max_cylinder`. The Banker matrices must have matching dimensions and allocations no greater than declared maxima. Invalid data is reported without crashing the menu.

## Sample results and interpretation

Run **5** to regenerate `report.txt`. On the included workload, the report compares average CPU waiting/turnaround, page fault counts/rates, and total disk-head movement. OPT uses future knowledge and is an idealized lower bound; real systems cannot generally know future page references. The sample Banker state should produce a safe sequence. These results are specific to the included input and are not universal claims.

## Test cases for manual verification

1. Run each menu option against the supplied data; confirm all four modules produce results and report writes `report.txt`.
2. Set a job arrival to `0`, and use a job with burst `1`; verify completion and non-negative waiting/turnaround.
3. Set a burst to `0`, duplicate a PID, or make the jobs file empty; confirm a readable validation error and that the menu remains available.
4. Use a page reference string with repeated pages; confirm hits occur, and faults never exceed the number of references.
5. Use a Banker state with insufficient available resources; confirm it is reported unsafe with unfinished processes.
6. Try a disk cylinder below `0` or above `max_cylinder`; confirm validation rejects it.
7. Press Ctrl+C or send end-of-input at the menu; confirm graceful exit.

## Design notes

The menu coordinates pure simulation functions, JSON datasets are kept separate from algorithms, and reporting consumes the same simulator results. This structure makes it straightforward to add algorithms or replace sample workloads without duplicating unrelated programs. Bash integration is provided as a thin launcher for environments that use Bash; the simulator logic remains in Python.
