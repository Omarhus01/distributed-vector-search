from dslabs import SimNetwork, SimScheduler

from src.storage_node import StorageNode

SONGS = {
    "Neon Run": [0.85, 0.75, 0.05],
    "City Lights": [0.70, 0.60, 0.20],
    "Sunday Coffee": [0.30, 0.40, 0.80],
    "Rainy Porch": [0.20, 0.30, 0.90],
}


def make_node():
    scheduler = SimScheduler()
    network = SimNetwork(scheduler, seed=1)
    inbox = []
    network.register("c1", inbox.append)  # fake coordinator: keeps every message it gets
    node = StorageNode("n1", ["c1", "n1"], network.endpoint("n1"), scheduler)
    network.register("n1", node.on_message)
    node.load_shard("S1", SONGS)
    return scheduler, network, inbox


def test_node_answers_search_with_local_top_k():
    scheduler, network, inbox = make_node()
    network.endpoint("c1").send("n1", {
        "type": "search", "query_id": 1, "shard": "S1", "vector": [0.80, 0.70, 0.10], "k": 2,
    })
    scheduler.run_until(1000)

    assert len(inbox) == 1
    reply = inbox[0]
    assert reply["type"] == "results"
    assert reply["query_id"] == 1
    assert [song_id for song_id, _ in reply["hits"]] == ["Neon Run", "City Lights"]


def test_node_answers_ping():
    scheduler, network, inbox = make_node()
    network.endpoint("c1").send("n1", {"type": "ping"})
    scheduler.run_until(1000)

    assert inbox[0]["type"] == "pong"

def test_node_reports_a_shard_it_does_not_hold():
    scheduler, network, inbox = make_node()
    network.endpoint("c1").send("n1", {
        "type": "search", "query_id": 2, "shard": "S9", "vector": [0.80, 0.70, 0.10], "k": 2,
    })
    scheduler.run_until(1000)

    assert inbox[0]["error"] == "n1 does not hold S9"
    assert "hits" not in inbox[0]