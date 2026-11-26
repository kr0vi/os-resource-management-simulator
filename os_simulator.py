#!/usr/bin/env python3
"""Integrated operating-system resource management simulator (Python 3.10+)."""
from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
LOG = ROOT / "activity.log"
logging.basicConfig(filename=LOG, level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")


def positive_int(value: Any, label: str, *, allow_zero: bool = False) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be an integer") from None
    if str(value).strip() != str(number) or number < (0 if allow_zero else 1):
        raise ValueError(f"{label} must be {'zero or a positive' if allow_zero else 'a positive'} integer")
    return number


def load_jobs(path: Path | None = None) -> list[dict[str, int]]:
    file = path or DATA / "sample_jobs.json"
    try:
        raw = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read jobs from {file}: {exc}") from exc
    if not isinstance(raw, list) or not raw:
        raise ValueError("Job data must be a non-empty JSON list")
    jobs = []
    seen = set()
    for i, row in enumerate(raw, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Job {i} must be an object")
        pid = str(row.get("pid", "")).strip()
        if not pid or pid in seen:
            raise ValueError(f"Job {i} has a missing or duplicate pid")
        seen.add(pid)
        jobs.append({"pid": pid,
                     "arrival": positive_int(row.get("arrival"), f"{pid} arrival", allow_zero=True),
                     "burst": positive_int(row.get("burst"), f"{pid} burst"),
                     "memory": positive_int(row.get("memory"), f"{pid} memory")})
    return jobs


def schedule(jobs: list[dict[str, int]], algorithm: str, quantum: int = 2) -> dict[str, Any]:
    """Non-preemptive FCFS/SJF and preemptive Round Robin; arrivals are honored."""
    algorithm = algorithm.upper()
    if algorithm not in {"FCFS", "SJF", "RR"}:
        raise ValueError("Algorithm must be FCFS, SJF, or RR")
    if algorithm == "RR":
        quantum = positive_int(quantum, "quantum")
    remaining = {j["pid"]: j["burst"] for j in jobs}
    starts, finishes, gantt = {}, {}, []
    now = min(j["arrival"] for j in jobs)
    waiting = []
    pending = sorted(jobs, key=lambda j: (j["arrival"], j["pid"]))
    ready: list[dict[str, int]] = []
    cursor = 0
    while len(finishes) < len(jobs):
        while cursor < len(pending) and pending[cursor]["arrival"] <= now:
            ready.append(pending[cursor]); cursor += 1
        if not ready:
            now = pending[cursor]["arrival"]
            continue
        if algorithm == "SJF":
            ready.sort(key=lambda j: (j["burst"], j["arrival"], j["pid"]))
        job = ready.pop(0); pid = job["pid"]
        starts.setdefault(pid, now)
        run = min(remaining[pid], quantum) if algorithm == "RR" else remaining[pid]
        end = now + run
        gantt.append({"pid": pid, "start": now, "end": end})
        remaining[pid] -= run; now = end
        while cursor < len(pending) and pending[cursor]["arrival"] <= now:
            ready.append(pending[cursor]); cursor += 1
        if remaining[pid]:
            ready.append(job)
        else:
            finishes[pid] = now
    metrics = []
    for j in jobs:
        turnaround = finishes[j["pid"]] - j["arrival"]
        metrics.append({"pid": j["pid"], "completion": finishes[j["pid"]],
                        "turnaround": turnaround, "waiting": turnaround - j["burst"]})
    return {"algorithm": algorithm, "gantt": gantt, "metrics": metrics,
            "avg_waiting": sum(x["waiting"] for x in metrics) / len(metrics),
            "avg_turnaround": sum(x["turnaround"] for x in metrics) / len(metrics)}


def memory_simulation(requests: list[int], capacity: int, frames: int = 3) -> dict[str, Any]:
    """Compare FIFO, LRU and OPT page replacement for a reference string."""
    capacity = positive_int(capacity, "page capacity")
    frames = positive_int(frames, "frame count")
    if not requests or any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in requests):
        raise ValueError("Reference string must contain non-negative integer page IDs")
    results = {}
    for alg in ("FIFO", "LRU", "OPT"):
        memory: list[int] = []; order: list[int] = []; faults = 0; trace = []
        for index, page in enumerate(requests):
            hit = page in memory
            if not hit:
                faults += 1
                if len(memory) < frames:
                    memory.append(page)
                else:
                    if alg == "FIFO": victim = order.pop(0)
                    elif alg == "LRU": victim = min(memory, key=lambda p: order.index(p))
                    else:
                        future = requests[index+1:]
                        victim = max(memory, key=lambda p: future.index(p) if p in future else math.inf)
                    memory[memory.index(victim)] = page
            if alg == "FIFO":
                # FIFO order changes only when a page is loaded, never on a hit.
                if not hit: order.append(page)
            else:
                # LRU tracks most-recent use; OPT does not need this order.
                if page in order: order.remove(page)
                order.append(page)
            trace.append({"page": page, "frames": memory.copy(), "hit": hit})
        results[alg] = {"faults": faults, "hits": len(requests)-faults,
                        "fault_rate": faults/len(requests), "trace": trace}
    return results


def banker_safety(available: list[int], maximum: list[list[int]], allocation: list[list[int]]) -> dict[str, Any]:
    """Banker's safety check. Returns a safe execution order or unfinished processes."""
    n = len(allocation)
    if n == 0 or len(maximum) != n or any(len(r) != len(available) for r in maximum+allocation):
        raise ValueError("Inconsistent process/resource matrix dimensions")
    if any(x < 0 for x in available) or any(x < 0 for row in maximum+allocation for x in row):
        raise ValueError("Resource counts cannot be negative")
    need = [[maximum[p][r]-allocation[p][r] for r in range(len(available))] for p in range(n)]
    if any(x < 0 for row in need for x in row):
        raise ValueError("Allocation cannot exceed a process maximum")
    work = available.copy(); done = [False]*n; order = []
    changed = True
    while changed:
        changed = False
        for p in range(n):
            if not done[p] and all(need[p][r] <= work[r] for r in range(len(work))):
                work = [work[r]+allocation[p][r] for r in range(len(work))]
                done[p] = True; order.append(f"P{p}"); changed = True
    return {"safe": all(done), "sequence": order, "unfinished": [f"P{i}" for i,d in enumerate(done) if not d], "need": need}


def disk_schedule(requests: list[int], head: int, max_cylinder: int) -> dict[str, Any]:
    """Compare FCFS, SSTF, SCAN, and C-SCAN (initial direction is upward)."""
    max_cylinder = positive_int(max_cylinder, "maximum cylinder")
    if not 0 <= head <= max_cylinder or any(not isinstance(x, int) or isinstance(x, bool) or not 0 <= x <= max_cylinder for x in requests):
        raise ValueError("Head and requests must be inside the cylinder range")
    if not requests: raise ValueError("At least one disk request is required")
    output = {}
    for alg in ("FCFS", "SSTF", "SCAN", "C-SCAN"):
        pending = list(requests); pos = head; path = [head]
        if alg == "FCFS": sequence = pending
        elif alg == "SSTF":
            sequence=[]
            while pending:
                nxt=min(pending,key=lambda x:(abs(x-pos),x)); pending.remove(nxt); sequence.append(nxt); pos=nxt
            pos=head
        elif alg == "SCAN": sequence=sorted(x for x in pending if x>=head)+[max_cylinder]+sorted((x for x in pending if x<head), reverse=True)
        else: sequence=sorted(x for x in pending if x>=head)+[max_cylinder,0]+sorted(x for x in pending if x<head)
        for x in sequence:
            if x != path[-1]: path.append(x)
        output[alg]={"path":path,"total_movement":sum(abs(b-a) for a,b in zip(path,path[1:]))}
    return output


def table(headers: list[str], rows: list[list[Any]]) -> str:
    widths = [max(len(str(h)), *(len(str(row[i])) for row in rows)) for i,h in enumerate(headers)]
    fmt = " | ".join("{:<"+str(w)+"}" for w in widths)
    return fmt.format(*headers)+"\n"+"-+-".join("-"*w for w in widths)+"\n"+"\n".join(fmt.format(*r) for r in rows)


def report() -> str:
    jobs = load_jobs(); lines = ["OS RESOURCE MANAGEMENT SIMULATOR - COMPARISON REPORT", "="*54, ""]
    schedules = [schedule(jobs,a) for a in ("FCFS","SJF","RR")]
    lines += ["CPU scheduling (lower is better)", table(["Algorithm","Avg waiting","Avg turnaround"],
             [[r["algorithm"],f"{r['avg_waiting']:.2f}",f"{r['avg_turnaround']:.2f}"] for r in schedules]), ""]
    pages=json.loads((DATA/"page_references.json").read_text())
    mem=memory_simulation(pages["references"],pages["frames"])
    lines += ["Page replacement",table(["Algorithm","Faults","Hits","Fault rate"],
             [[a,str(x["faults"]),str(x["hits"]),f"{x['fault_rate']:.1%}"] for a,x in mem.items()]), ""]
    d=json.loads((DATA/"disk_requests.json").read_text()); disk=disk_schedule(d["requests"],d["head"],d["max_cylinder"])
    lines += ["Disk scheduling (lower movement is better)",table(["Algorithm","Movement","Service path"],
             [[a,str(x["total_movement"])," -> ".join(map(str,x["path"]))] for a,x in disk.items()]), ""]
    lines += ["Observations", "- SJF favors short jobs; FCFS preserves arrival order; Round Robin shares CPU in time slices.",
              "- OPT is a theoretical page-replacement lower bound because it knows future references.",
              "- Disk movement depends on the initial head and direction; SCAN-family methods sweep the disk.",
              "- Results describe these sample inputs and are not universal performance guarantees."]
    return "\n".join(lines)


def show_schedule():
    jobs=load_jobs()
    for alg in ("FCFS","SJF","RR"):
        r=schedule(jobs,alg)
        print(f"\n{alg} Gantt: "+" | ".join(f"{x['pid']}[{x['start']}-{x['end']}]" for x in r["gantt"]))
        print(table(["PID","Completion","Turnaround","Waiting"],[[m[k] for k in ("pid","completion","turnaround","waiting")] for m in r["metrics"]]))
        print(f"Average waiting: {r['avg_waiting']:.2f}; average turnaround: {r['avg_turnaround']:.2f}")


def main():
    menu = "\nOS Resource Management Simulator\n1. CPU scheduling\n2. Page replacement\n3. Deadlock safety (Banker's algorithm)\n4. Disk scheduling\n5. Generate comparison report\n0. Exit\nChoice: "
    while True:
        try:
            choice=input(menu).strip()
            if choice=="0": print("Goodbye."); break
            if choice=="1": show_schedule()
            elif choice=="2":
                d=json.loads((DATA/"page_references.json").read_text()); result=memory_simulation(d["references"],d["frames"])
                print(table(["Algorithm","Faults","Hits","Fault rate"],[[a,x["faults"],x["hits"],f"{x['fault_rate']:.1%}"] for a,x in result.items()]))
            elif choice=="3":
                d=json.loads((DATA/"banker_example.json").read_text()); result=banker_safety(d["available"],d["maximum"],d["allocation"])
                print("Safe state" if result["safe"] else "Unsafe state", "-", " -> ".join(result["sequence"]) or "no safe process")
                if result["unfinished"]: print("Cannot proceed:", ", ".join(result["unfinished"]))
            elif choice=="4":
                d=json.loads((DATA/"disk_requests.json").read_text()); result=disk_schedule(d["requests"],d["head"],d["max_cylinder"])
                print(table(["Algorithm","Movement","Path"],[[a,x["total_movement"]," -> ".join(map(str,x["path"]))] for a,x in result.items()]))
            elif choice=="5":
                text=report(); print("\n"+text); out=ROOT/"report.txt"; out.write_text(text+"\n",encoding="utf-8"); print(f"\nSaved {out.name}")
            else: print("Choose one of the listed options.")
            logging.info("Completed menu choice %r",choice)
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            print(f"Input/data error: {exc}"); logging.warning("Handled error: %s",exc)
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye."); break


if __name__ == "__main__": main()
