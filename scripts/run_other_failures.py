"""Run failures that are not crashes: a slow node and a lossy network.

Each run has three phases: no failure, the failure, the failure removed. Each
shard has 2 copies. Prints recall for each phase and saves a viewer file in
results/.

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
    """Run the three phases for one failure.

    Args:
        songs: list of song dicts.
        queries: list of query dicts.
        name: scenario name, used for the viewer file name.
        cause_failure: function that takes the cluster, starts the failure
            and returns its rule.

    Returns:
        Tuple (before, during, after) of average recall. Saves the viewer file.
    """
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
    """Run every scenario in SCENARIOS and print recall for each phase."""
    songs = json.loads(Path("data/songs.json").read_text())
    queries = json.loads(Path("data/queries.json").read_text())

    print(f"{'failure':<16}{'before':>8}{'during':>8}{'after':>8}")
    for name, cause_failure in SCENARIOS:
        before, during, after = run_scenario(songs, queries, name, cause_failure)
        print(f"{name:<16}{before:>8.2f}{during:>8.2f}{after:>8.2f}")
    print(f"viewers saved in {RESULTS_DIR}/")


if __name__ == "__main__":
    main()