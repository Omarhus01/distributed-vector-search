"""Failures that aren't crashes: one slow node, and a network that loses messages.

Each run: all nodes fine, then the failure, then fixed. Uses 2 copies of each shard.
Run from the repo root:  python -m scripts.run_other_failures
"""
import json
from pathlib import Path

from scripts.run_crash import RESULTS_DIR, run_phase
from src.cluster_setup import build_cluster
from src.faults import lose_messages, remove_fault, slow_down

SCENARIOS = [  # (name, how to cause the failure)
    ("slow_n2", lambda cluster: slow_down(cluster, "n2", 600)),
    ("lossy_network", lambda cluster: lose_messages(cluster, 0.1)),
]


def run_scenario(songs, queries, name, cause_failure):
    cluster = build_cluster(songs)
    before = run_phase(cluster, queries)

    rule = cause_failure(cluster)
    during = run_phase(cluster, queries)

    remove_fault(cluster, rule)
    cluster.scheduler.run_until(cluster.scheduler.now_ms() + 1000)
    after = run_phase(cluster, queries)

    RESULTS_DIR.mkdir(exist_ok=True)
    cluster.scheduler.trace.save_viewer(RESULTS_DIR / f"{name}.html")
    return before, during, after


def main():
    songs = json.loads(Path("data/songs.json").read_text())
    queries = json.loads(Path("data/queries.json").read_text())

    print(f"{'failure':<16}{'before':>8}{'during':>8}{'after':>8}")
    for name, cause_failure in SCENARIOS:
        before, during, after = run_scenario(songs, queries, name, cause_failure)
        print(f"{name:<16}{before:>8.2f}{during:>8.2f}{after:>8.2f}")
    print(f"viewers saved in {RESULTS_DIR}/")


if __name__ == "__main__":
    main()