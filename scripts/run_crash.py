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
CRASHED_NODE = "n2"
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


def main():
    songs = json.loads(Path("data/songs.json").read_text())
    queries = json.loads(Path("data/queries.json").read_text())
    cluster = build_cluster(songs)

    before = run_phase(cluster, queries)

    crash(cluster, CRASHED_NODE)
    during = run_phase(cluster, queries)

    recover(cluster, CRASHED_NODE)
    cluster.scheduler.run_until(cluster.scheduler.now_ms() + 1000)  # one heartbeat to notice it's back
    after = run_phase(cluster, queries)

    print(f"recall@{K} before crash:       {before:.2f}")
    print(f"recall@{K} with {CRASHED_NODE} crashed:  {during:.2f}")
    print(f"recall@{K} after recovery:     {after:.2f}")
    print("node status at the end:", cluster.coordinator.status)

    RESULTS_DIR.mkdir(exist_ok=True)
    viewer = cluster.scheduler.trace.save_viewer(RESULTS_DIR / "crash_n2.html")
    print(f"viewer saved to {viewer}")


if __name__ == "__main__":
    main()