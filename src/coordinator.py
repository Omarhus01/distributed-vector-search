"""Coordinator: sends queries to shards, merges the replies, tracks node health."""
import zlib
from dataclasses import dataclass, field

from dslabs.protocols import Message, Scheduler, Transport


def shard_for(song_id, num_shards):
    """Return the id of the shard that holds a song, such as "S2".

    Uses crc32 instead of hash() because hash() gives a different result on
    each run of Python.
    """
    return f"S{zlib.crc32(song_id.encode()) % num_shards + 1}"


@dataclass
class Coordinator:
    """Receives queries, sends each one to the shards and merges the replies.

    Each shard can be stored on several nodes (shard_map, primary first). For
    each query the coordinator asks one node per shard. It pings all nodes on
    a timer and marks each node alive, suspected or dead by how long the node
    has been silent. A query ends when every shard answered or after
    query_timeout_ms.
    """

    node_id: str
    peers: list[str]
    transport: Transport
    scheduler: Scheduler
    shard_map: dict[str, list[str]] = field(default_factory=dict)  # shard -> nodes holding it, primary first
    query_timeout_ms: int = 1000
    pending: dict[int, dict] = field(default_factory=dict)   # query_id -> query still waiting
    finished: dict[int, dict] = field(default_factory=dict)  # query_id -> final answer
    next_query_id: int = 1
    heartbeat_ms: int = 500
    suspect_after_ms: int = 1000  # silent this long: suspected
    dead_after_ms: int = 2000     # silent this long: dead
    last_heard: dict[str, int] = field(default_factory=dict)  # node -> time of its last pong
    status: dict[str, str] = field(default_factory=dict)      # node -> alive / suspected / dead

    def search(self, vector, k):
        """Start a query and return its query id.

        Sends the search to one node per shard. The answer appears in
        self.finished[query_id] when all shards reply or the timeout passes.

        Args:
            vector: the query vector.
            k: number of songs to return.
        """
        query_id = self.next_query_id
        self.next_query_id += 1

        # one node per shard: alive first, else suspected
        chosen = {}
        for shard, nodes in self.shard_map.items():
            node = self.pick_node(nodes)
            if node is not None:
                chosen[shard] = node
        skipped = sorted(set(self.shard_map) - set(chosen))
        self.pending[query_id] = {"k": k, "waiting_for": set(chosen), "skipped": skipped,
                                  "hits": [], "errors": {}}

        if not chosen:
            self.finish(query_id)  # no node to ask for any shard
            return query_id

        for shard, node in chosen.items():
            self.transport.send(node, {
                "type": "search", "query_id": query_id, "shard": shard, "vector": vector, "k": k,
            })

        def timeout():
            self.finish(query_id)

        self.pending[query_id]["cancel_timeout"] = self.scheduler.call_later(self.query_timeout_ms, timeout)
        return query_id

    def pick_node(self, nodes):
        """Return the node to ask for a shard.

        Args:
            nodes: nodes that hold the shard, primary first.

        Returns:
            The first alive node. If none is alive, the first suspected node.
            If all are dead, None.
        """
        for wanted in ("alive", "suspected"):
            for node in nodes:
                if self.status.get(node, "alive") == wanted:
                    return node
        return None

    def on_message(self, msg: Message) -> None:
        """Handle a results or pong message. Raises ValueError for other types."""
        if msg["type"] == "results":
            self.handle_results(msg)
        elif msg["type"] == "pong":
            self.last_heard[msg["from"]] = self.scheduler.now_ms()
            self.check_nodes()
        else:
            raise ValueError(f"Unknown message type in {msg!r}")

    def handle_results(self, msg):
        """Add one shard's reply to its query.

        Finishes the query when every shard has replied. Ignores replies for
        queries that finished.
        """
        query = self.pending.get(msg["query_id"])
        if query is None:
            return  # late reply; the query is finished
        query["waiting_for"].discard(msg["shard"])
        if "error" in msg:
            query["errors"][msg["shard"]] = msg["error"]
        else:
            query["hits"].extend(msg["hits"])
        if not query["waiting_for"]:
            query["cancel_timeout"]()
            self.finish(msg["query_id"])

    def finish(self, query_id):
        """End a query and store its answer in self.finished.

        The answer is a dict with:
            hits: top k songs from the replies, as [song_id, distance].
            missing_shards: shards with no reply or no node to ask.
            errors: {shard: error text} from nodes that replied with an error.
        """
        query = self.pending.pop(query_id, None)
        if query is None:
            return
        merged = sorted(query["hits"], key=lambda hit: (hit[1], hit[0]))[: query["k"]]
        self.finished[query_id] = {
            "hits": merged,
            "missing_shards": sorted(set(query["waiting_for"]) | set(query["skipped"])),
            "errors": query["errors"],
        }

    def brief_state(self):
        """Return node status and query counts for the viewer."""
        return {"nodes": dict(self.status), "waiting": len(self.pending), "done": len(self.finished)}

    def start(self):
        """Mark every node alive and start the heartbeat."""
        for node in {node for nodes in self.shard_map.values() for node in nodes}:
            self.last_heard[node] = self.scheduler.now_ms()
            self.status[node] = "alive"
        self.heartbeat()

    def heartbeat(self):
        """Ping every node, update node status and schedule the next heartbeat."""
        for node in self.last_heard:
            self.transport.send(node, {"type": "ping"})
        self.check_nodes()
        self.scheduler.call_later(self.heartbeat_ms, self.heartbeat)

    def check_nodes(self):
        """Update each node's status from the time since its last pong.

        Silent for suspect_after_ms: suspected. Silent for dead_after_ms: dead.
        Otherwise alive. Each change is logged.
        """
        now = self.scheduler.now_ms()
        for node, heard in self.last_heard.items():
            silent = now - heard
            if silent >= self.dead_after_ms:
                new_status = "dead"
            elif silent >= self.suspect_after_ms:
                new_status = "suspected"
            else:
                new_status = "alive"
            if new_status != self.status[node]:
                self.transport.note(f"{node}: {self.status[node]} -> {new_status}")
                self.status[node] = new_status