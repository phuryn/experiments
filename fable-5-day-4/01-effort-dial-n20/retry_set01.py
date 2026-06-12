#!/usr/bin/env python3
"""Retry harness for Set 01: re-runs only combos that lack a clean (rc=0) row.

Idempotent — safe to re-invoke after another session-limit hit; appends to the
same tagged CSV, analyzer ignores rc!=0 rows. Usage:
  python retry_set01.py --tag v4 --rounds 1-20
"""
import csv, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_set01 as h  # reuse lanes, claude_cmd, log_row, run_one, paths


def main():
    expected = h.build_runs()  # honors --rounds
    clean = set()
    if os.path.exists(h.csv_path):
        with open(h.csv_path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["rc"] == "0":
                    clean.add((r["tier"], r["model"], r["effort"], int(r["round"])))
    todo = [run for run in expected if (run[0], run[1], run[2], run[3]) not in clean]
    print(f"expected={len(expected)} clean={len(clean)} retrying={len(todo)}")
    if not todo:
        print("SET01 RETRY: nothing to do, all clean")
        return
    lanes = [todo[i::h.LANES] for i in range(h.LANES)]
    import threading, time
    threads = [threading.Thread(target=h.lane_worker, args=(i, jobs)) for i, jobs in enumerate(lanes)]
    t0 = time.monotonic()
    for t in threads: t.start()
    for t in threads: t.join()
    print(f"SET01 RETRY DONE: {len(todo)} runs in {round((time.monotonic()-t0)/60,1)} min")


if __name__ == "__main__":
    main()
