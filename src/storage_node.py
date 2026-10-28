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
        reply = {"type": "results", "query_id": msg["query_id"], "shard": msg["shard"]}
        if msg["shard"] not in self.shards:
            # Say so, instead of answering with nothing: an empty answer would hide the mistake.
            reply["error"] = f"{self.node_id} does not hold {msg['shard']}"
        else:
            reply["hits"] = top_k(msg["vector"], self.shards[msg["shard"]], msg["k"])
        self.transport.send(msg["from"], reply)

    def brief_state(self):
        return {shard_id: len(songs) for shard_id, songs in self.shards.items()}