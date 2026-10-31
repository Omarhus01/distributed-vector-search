"""Crash a storage node in the middle of a run and measure what it costs.

Phase 1: all nodes up. Phase 2: n2 crashed. Phase 3: n2 recovered.
Run from the repo root:  python -m scripts.run_crash
"""
import json
from pathlib import Path

from src.cluster_setup import build_cluster
from src.faults import crash, recover
from src.metrics import recall_at_k

K = 5
GAP_MS = 300
SCENARIOS = [  # (replication factor, nodes to crash)
    (1, ["n2"]),
    (2, ["n2"]),
    (2, ["n2", "n3"]),
    (3, ["n2", "n3"]),
]
RESULTS_DIR = Path("results")


def run_phase(cluster, queries):
    """Send every query, one every GAP_MS, wait for the answers, return the average recall."""
    start = cluster.scheduler.now_ms()
    asked = []
    for i, query in enumerate(queries):
        cluster.scheduler.trace.client("c1", f"search: {query['name']}")
        asked.append((query, cluster.coordinator.search(query["vector"], K)))
        cluster.scheduler.run_until(start + (i + 1) * GAP_MS)
    cluster.scheduler.run_until(cluster.scheduler.now_ms() + 1500)  # let the last answers arrive

    recalls = []
    for query, query_id in asked:
        returned = [song_id for song_id, _ in cluster.coordinator.finished[query_id]["hits"]]
        expected = [song_id for song_id, _ in query["true_top_k"]]
        recalls.append(recall_at_k(returned, expected))
    return sum(recalls) / len(recalls)


def run_scenario(songs, queries, replication_factor, crashed_nodes):
    """Crash the given nodes mid-run, return recall before, during, and after. Saves the viewer."""
    cluster = build_cluster(songs, replication_factor=replication_factor)
    before = run_phase(cluster, queries)

    for node_id in crashed_nodes:
        crash(cluster, node_id)
    during = run_phase(cluster, queries)

    for node_id in crashed_nodes:
        recover(cluster, node_id)
    cluster.scheduler.run_until(cluster.scheduler.now_ms() + 1000)  # one heartbeat to notice they're back
    after = run_phase(cluster, queries)

    name = f"crash_{replication_factor}_copies_{'_'.join(crashed_nodes)}_down"
    RESULTS_DIR.mkdir(exist_ok=True)
    cluster.scheduler.trace.save_viewer(RESULTS_DIR / f"{name}.html")
    return before, during, after


def main():
    songs = json.loads(Path("data/songs.json").read_text())
    queries = json.loads(Path("data/queries.json").read_text())

    print(f"{'copies':<8}{'crashed':<10}{'before':>8}{'during':>8}{'after':>8}")
    for replication_factor, crashed_nodes in SCENARIOS:
        before, during, after = run_scenario(songs, queries, replication_factor, crashed_nodes)
        print(f"{'RF=' + str(replication_factor):<8}{'+'.join(crashed_nodes):<10}"
              f"{before:>8.2f}{during:>8.2f}{after:>8.2f}")
    print(f"viewers saved in {RESULTS_DIR}/")


if __name__ == "__main__":
    main()