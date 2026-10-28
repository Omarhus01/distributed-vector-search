from dslabs import SimNetwork, SimScheduler

from src.coordinator import Coordinator, shard_for
from src.storage_node import StorageNode

QUERY = [0.80, 0.70, 0.10]  # Night Drive


def make_cluster(n2_answers=True, shard_map=None):
    scheduler = SimScheduler()
    network = SimNetwork(scheduler, seed=1)
    ids = ["c1", "n1", "n2"]

    shard_map = shard_map or {"S1": "n1", "S2": "n2"}
    coordinator = Coordinator("c1", ids, network.endpoint("c1"), scheduler, shard_map=shard_map)
    network.register("c1", coordinator.on_message)

    n1 = StorageNode("n1", ids, network.endpoint("n1"), scheduler)
    n1.load_shard("S1", {"Neon Run": [0.85, 0.75, 0.05], "Rainy Porch": [0.20, 0.30, 0.90]})
    network.register("n1", n1.on_message)

    if n2_answers:
        n2 = StorageNode("n2", ids, network.endpoint("n2"), scheduler)
        n2.load_shard("S2", {"City Lights": [0.70, 0.60, 0.20], "Sunday Coffee": [0.30, 0.40, 0.80]})
        network.register("n2", n2.on_message)
    else:
        network.register("n2", lambda msg: None)  # a node that receives but never answers

    return scheduler, coordinator


def hit_ids(answer):
    return [song_id for song_id, _ in answer["hits"]]


def test_merges_results_from_all_shards():
    scheduler, coordinator = make_cluster()
    query_id = coordinator.search(QUERY, 2)
    scheduler.run_until(2000)

    answer = coordinator.finished[query_id]
    assert hit_ids(answer) == ["Neon Run", "City Lights"]
    assert answer["missing_shards"] == []
    assert answer["errors"] == {}


def test_returns_partial_results_when_a_shard_never_answers():
    scheduler, coordinator = make_cluster(n2_answers=False)
    query_id = coordinator.search(QUERY, 2)
    scheduler.run_until(2000)

    answer = coordinator.finished[query_id]
    assert hit_ids(answer) == ["Neon Run", "Rainy Porch"]
    assert answer["missing_shards"] == ["S2"]


def test_reports_a_shard_sent_to_the_wrong_node():
    # Wiring mistake: S2 is sent to n1, which only holds S1.
    scheduler, coordinator = make_cluster(shard_map={"S1": "n1", "S2": "n1"})
    query_id = coordinator.search(QUERY, 2)
    scheduler.run_until(2000)

    answer = coordinator.finished[query_id]
    assert answer["errors"] == {"S2": "n1 does not hold S2"}
    assert hit_ids(answer) == ["Neon Run", "Rainy Porch"]


def test_shard_for_is_the_same_every_time():
    # Fixed number, not Python's hash(), which changes every time Python starts.
    assert shard_for("4qPNDBW1i3p13qLCt0Ki3A", 3) == shard_for("4qPNDBW1i3p13qLCt0Ki3A", 3)
    assert shard_for("4qPNDBW1i3p13qLCt0Ki3A", 3) in {"S1", "S2", "S3"}

def test_silent_node_becomes_suspected_then_dead():
    scheduler, coordinator = make_cluster(n2_answers=False)
    coordinator.start()

    scheduler.run_until(1200)
    assert coordinator.status == {"n1": "alive", "n2": "suspected"}

    scheduler.run_until(2200)
    assert coordinator.status == {"n1": "alive", "n2": "dead"}


def test_dead_node_is_skipped_without_waiting():
    scheduler, coordinator = make_cluster(n2_answers=False)
    coordinator.start()
    scheduler.run_until(2200)  # n2 is dead by now

    query_id = coordinator.search(QUERY, 2)
    scheduler.run_until(2500)  # only 300 ms later, well before the 1 s timeout

    answer = coordinator.finished[query_id]
    assert answer["missing_shards"] == ["S2"]
    assert hit_ids(answer) == ["Neon Run", "Rainy Porch"]