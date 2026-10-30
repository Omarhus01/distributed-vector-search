"""Build the simulated cluster: one coordinator and three storage nodes."""
from dataclasses import dataclass, field

from dslabs import SimNetwork, SimScheduler

from src.coordinator import Coordinator, shard_for
from src.storage_node import StorageNode

STORAGE_NODES = ["n1", "n2", "n3"]
SHARDS = ["S1", "S2", "S3"]  # shard i's primary is STORAGE_NODES[i]


def placement(replication_factor):
    """shard -> the nodes that hold it, primary first.

    Each copy goes to the node before it in the list, wrapping around (Figure 2 in my proposal).
    replication_factor 2: S1 -> [n1, n3], S2 -> [n2, n1], S3 -> [n3, n2].
    """
    if not 1 <= replication_factor <= len(STORAGE_NODES):
        raise ValueError(f"replication_factor must be between 1 and {len(STORAGE_NODES)}")
    n = len(STORAGE_NODES)
    return {shard: [STORAGE_NODES[(i - j) % n] for j in range(replication_factor)]
            for i, shard in enumerate(SHARDS)}

@dataclass
class SimCluster:
    scheduler: SimScheduler
    network: SimNetwork
    coordinator: Coordinator
    nodes: dict[str, StorageNode]
    crashed: dict = field(default_factory=dict)  # node -> the rule that cut it off


def split_into_shards(songs):
    """Put each song in the shard its id hashes to."""
    shards = {shard: {} for shard in SHARDS}
    for song in songs:
        shards[shard_for(song["id"], len(SHARDS))][song["id"]] = song["vector"]
    return shards


def build_cluster(songs, seed=1, replication_factor=2):
    scheduler = SimScheduler()
    network = SimNetwork(scheduler, seed=seed)
    all_ids = ["c1"] + STORAGE_NODES
    shard_map = placement(replication_factor)

    nodes = {node_id: StorageNode(node_id, all_ids, network.endpoint(node_id), scheduler)
             for node_id in STORAGE_NODES}
    for shard, songs_in_shard in split_into_shards(songs).items():
        for node_id in shard_map[shard]:
            nodes[node_id].load_shard(shard, songs_in_shard)

    coordinator = Coordinator("c1", all_ids, network.endpoint("c1"), scheduler, shard_map=shard_map)

    # Register after loading, so the viewer's first snapshot already shows the shard sizes.
    for node_id, node in nodes.items():
        network.register(node_id, node.on_message)
    network.register("c1", coordinator.on_message)

    coordinator.start()

    return SimCluster(scheduler, network, coordinator, nodes)