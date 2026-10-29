"""Run the test queries through the cluster, measure recall@5, save the viewer.

Run from the repo root:  python -m scripts.run_queries
"""
import json
from pathlib import Path

from src.cluster_setup import build_cluster
from src.metrics import recall_at_k

K = 5
GAP_MS = 300  # time between queries, so the viewer shows them one at a time
RESULTS_DIR = Path("results")


def main():
    songs = json.loads(Path("data/songs.json").read_text())
    queries = json.loads(Path("data/queries.json").read_text())
    cluster = build_cluster(songs)
    print("songs per node:", {node_id: node.brief_state() for node_id, node in cluster.nodes.items()})

    query_ids = []
    for i, query in enumerate(queries):
        cluster.scheduler.trace.client("c1", f"search: {query['name']}")
        query_ids.append(cluster.coordinator.search(query["vector"], K))
        cluster.scheduler.run_until((i + 1) * GAP_MS)
    cluster.scheduler.run_until(len(queries) * GAP_MS + 2000)  # let the last replies arrive

    recalls = []
    for query, query_id in zip(queries, query_ids):
        answer = cluster.coordinator.finished[query_id]
        returned = [song_id for song_id, _ in answer["hits"]]
        expected = [song_id for song_id, _ in query["true_top_k"]]
        recalls.append(recall_at_k(returned, expected))
    print(f"recall@{K}: {sum(recalls) / len(recalls):.2f} over {len(recalls)} queries")

    RESULTS_DIR.mkdir(exist_ok=True)
    viewer = cluster.scheduler.trace.save_viewer(RESULTS_DIR / "first_run.html")
    print(f"viewer saved to {viewer}")


if __name__ == "__main__":
    main()