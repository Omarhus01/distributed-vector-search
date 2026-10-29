"""Build the simulated cluster: one coordinator and three storage nodes."""
from dataclasses import dataclass, field

from dslabs import SimNetwork, SimScheduler

from src.coordinator import Coordinator, shard_for
from src.storage_node import StorageNode

STORAGE_NODES = ["n1", "n2", "n3"]
PLACEMENT = {"S1": "n1", "S2": "n2", "S3": "n3"}  # shard -> node that holds it


@dataclass
class SimCluster:
    scheduler: SimScheduler
    network: SimNetwork
    coordinator: Coordinator
    nodes: dict[str, StorageNode]
    crashed: dict = field(default_factory=dict)  # node -> the rule that cut it off


def split_into_shards(songs):
    """Put each song in the shard its id hashes to."""
    shards = {shard: {} for shard in PLACEMENT}
    for song in songs:
        shards[shard_for(song["id"], len(PLACEMENT))][song["id"]] = song["vector"]
    return shards


def build_cluster(songs, seed=1):
    scheduler = SimScheduler()
    network = SimNetwork(scheduler, seed=seed)
    all_ids = ["c1"] + STORAGE_NODES

    nodes = {node_id: StorageNode(node_id, all_ids, network.endpoint(node_id), scheduler)
             for node_id in STORAGE_NODES}
    for shard, songs_in_shard in split_into_shards(songs).items():
        nodes[PLACEMENT[shard]].load_shard(shard, songs_in_shard)

    coordinator = Coordinator("c1", all_ids, network.endpoint("c1"), scheduler, shard_map=dict(PLACEMENT))

    # Register after loading, so the viewer's first snapshot already shows the shard sizes.
    for node_id, node in nodes.items():
        network.register(node_id, node.on_message)
    network.register("c1", coordinator.on_message)

    coordinator.start()

    return SimCluster(scheduler, network, coordinator, nodes)