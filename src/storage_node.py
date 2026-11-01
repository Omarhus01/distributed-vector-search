"""Storage node: holds shards of songs and answers searches."""
from dataclasses import dataclass, field

from dslabs.protocols import Message, Scheduler, Transport

from src.similarity import top_k


@dataclass
class StorageNode:
    """A node that stores shards and answers search and ping messages.

    A shard is one slice of the song collection, stored as {song_id: vector}.
    A node can hold several shards: its own and copies of other nodes' shards.
    """

    node_id: str
    peers: list[str]
    transport: Transport
    scheduler: Scheduler
    shards: dict[str, dict[str, list[float]]] = field(default_factory=dict)

    def load_shard(self, shard_id, songs):
        """Store a shard on this node.

        Args:
            shard_id: name of the shard, such as "S1".
            songs: dict of {song_id: vector}.
        """
        self.shards[shard_id] = dict(songs)

    def on_message(self, msg: Message) -> None:
        """Handle a message from the network.

        A search message gets a results reply. A ping message gets a pong
        reply. Raises ValueError for other message types.
        """
        if msg["type"] == "search":
            self.handle_search(msg)
        elif msg["type"] == "ping":
            self.transport.send(msg["from"], {"type": "pong"})
        else:
            raise ValueError(f"Unknown message type in {msg!r}")

    def handle_search(self, msg):
        """Search one shard and send the result to the sender.

        The reply holds the top k songs of the shard. If this node does not
        hold the shard, the reply holds an error text instead.
        """
        reply = {"type": "results", "query_id": msg["query_id"], "shard": msg["shard"]}
        if msg["shard"] not in self.shards:
            # an empty reply would hide a wrong shard id, so send an error
            reply["error"] = f"{self.node_id} does not hold {msg['shard']}"
        else:
            reply["hits"] = top_k(msg["vector"], self.shards[msg["shard"]], msg["k"])
        self.transport.send(msg["from"], reply)

    def brief_state(self):
        """Return {shard_id: number of songs} for the viewer."""
        return {shard_id: len(songs) for shard_id, songs in self.shards.items()}