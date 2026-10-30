import json
from pathlib import Path

from src.cluster_setup import build_cluster
from src.faults import crash, recover, slow_down

SONGS = json.loads(Path("data/songs.json").read_text())


def test_crashed_node_is_declared_dead():
    cluster = build_cluster(SONGS)
    cluster.scheduler.run_until(1000)
    crash(cluster, "n2")
    cluster.scheduler.run_until(4000)

    assert cluster.coordinator.status["n2"] == "dead"
    assert cluster.coordinator.status["n1"] == "alive"


def test_recovered_node_comes_back_alive():
    cluster = build_cluster(SONGS)
    crash(cluster, "n2")
    cluster.scheduler.run_until(4000)
    recover(cluster, "n2")
    cluster.scheduler.run_until(5000)

    assert cluster.coordinator.status["n2"] == "alive"
    assert cluster.crashed == {}

def test_slow_node_stays_alive_but_its_answers_time_out():
    cluster = build_cluster(SONGS)
    slow_down(cluster, "n2", 600)
    cluster.scheduler.run_until(3000)
    assert cluster.coordinator.status["n2"] == "alive"  # its pongs still arrive, just late

    query_id = cluster.coordinator.search(SONGS[0]["vector"], 5)
    cluster.scheduler.run_until(5000)
    assert cluster.coordinator.finished[query_id]["missing_shards"] == ["S2"]  # its reply came after the 1 s timeout