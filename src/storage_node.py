from dataclasses import dataclass, field

from dslabs.protocols import Message, Scheduler, Transport

from src.vectors import top_k


@dataclass
class StorageNode:
    """Holds shards of songs and answers searches over them.

    A shard is a dict of {song_id: vector}. A node can hold several shards:
    its own, and later a replica of another node's shard.
    """

    node_id: str
    peers: list[str]
    transport: Transport
    scheduler: Scheduler
    shards: dict[str, dict[str, list[float]]] = field(default_factory=dict)

    def load_shard(self, shard_id, songs):
        """Store a shard on this node. songs: dict of {song_id: vector}."""
        self.shards[shard_id] = dict(songs)

    def on_message(self, msg: Message) -> None:
        if msg["type"] == "search":
            self.handle_search(msg)
        elif msg["type"] == "ping":
            self.transport.send(msg["from"], {"type": "pong"})
        else:
            raise ValueError(f"Unknown message type in {msg!r}")

    def handle_search(self, msg):
        shard = self.shards.get(msg["shard"], {})
        hits = top_k(msg["vector"], shard, msg["k"])
        self.transport.send(msg["from"], {
            "type": "results",
            "query_id": msg["query_id"],
            "shard": msg["shard"],
            "hits": hits,
        })