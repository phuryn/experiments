#!/usr/bin/env python3
"""Retry harness for Set 02: re-runs only combos lacking a clean (rc=0) row.

Idempotent — safe after a session-limit hit; appends to the tagged CSV.
Usage: python retry_set02.py --tag v4 --rounds 1-20
"""
import csv, os, sys, threading, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_set02 as h


def main():
    expected = h.build_runs()  # honors --rounds
    clean = set()
    if os.path.exists(h.csv_path):
        with open(h.csv_path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["rc"] == "0":
                    clean.add((r["exp"], r["model"], r["q"], int(r["round"])))
    todo = [run for run in expected if (run[0], run[1], run[3], run[4]) not in clean]
    print(f"expected={len(expected)} clean={len(clean)} retrying={len(todo)}")
    if not todo:
        print("SET02 RETRY: nothing to do, all clean")
        return
    lanes = [todo[i::h.LANES] for i in range(h.LANES)]
    threads = [threading.Thread(target=h.lane_worker, args=(i, jobs)) for i, jobs in enumerate(lanes)]
    t0 = time.monotonic()
    for t in threads: t.start()
    for t in threads: t.join()
    print(f"SET02 RETRY DONE: {len(todo)} runs in {round((time.monotonic()-t0)/60,1)} min")


if __name__ == "__main__":
    main()
