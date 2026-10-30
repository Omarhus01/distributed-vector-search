import zlib
from dataclasses import dataclass, field

from dslabs.protocols import Message, Scheduler, Transport


def shard_for(song_id, num_shards):
    """Which shard a song lives on. crc32 gives the same number on every run and every machine."""
    return f"S{zlib.crc32(song_id.encode()) % num_shards + 1}"


@dataclass
class Coordinator:
    """Sends each query to every shard, merges the replies into one top-k."""

    node_id: str
    peers: list[str]
    transport: Transport
    scheduler: Scheduler
    shard_map: dict[str, str] = field(default_factory=dict)  # shard -> node that holds it
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
        """Start a query. The answer appears in self.finished[query_id]."""
        query_id = self.next_query_id
        self.next_query_id += 1

        # Don't ask nodes already known to be dead; suspected ones are still asked.
        live = {shard: node for shard, node in self.shard_map.items()
                if self.status.get(node, "alive") != "dead"}
        skipped = sorted(set(self.shard_map) - set(live))
        self.pending[query_id] = {"k": k, "waiting_for": set(live), "skipped": skipped,
                                "hits": [], "errors": {}}

        if not live:
            self.finish(query_id)  # nobody to ask
            return query_id

        for shard, node in live.items():
            self.transport.send(node, {
                "type": "search", "query_id": query_id, "shard": shard, "vector": vector, "k": k,
            })

        def timeout():
            self.finish(query_id)

        self.pending[query_id]["cancel_timeout"] = self.scheduler.call_later(self.query_timeout_ms, timeout)
        return query_id

    def on_message(self, msg: Message) -> None:
        if msg["type"] == "results":
            self.handle_results(msg)
        elif msg["type"] == "pong":
            self.last_heard[msg["from"]] = self.scheduler.now_ms()
            self.check_nodes()
        else:
            raise ValueError(f"Unknown message type in {msg!r}")

    def handle_results(self, msg):
        query = self.pending.get(msg["query_id"])
        if query is None:
            return  # reply came after the timeout; the query is already finished
        query["waiting_for"].discard(msg["shard"])
        if "error" in msg:
            query["errors"][msg["shard"]] = msg["error"]
        else:
            query["hits"].extend(msg["hits"])
        if not query["waiting_for"]:
            query["cancel_timeout"]()
            self.finish(msg["query_id"])

    def finish(self, query_id):
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
        return {"nodes": dict(self.status), "waiting": len(self.pending), "done": len(self.finished)}

    def start(self):
        """Begin heartbeats. Every node counts as alive at the start."""
        for node in set(self.shard_map.values()):
            self.last_heard[node] = self.scheduler.now_ms()
            self.status[node] = "alive"
        self.heartbeat()

    def heartbeat(self):
        for node in self.last_heard:
            self.transport.send(node, {"type": "ping"})
        self.check_nodes()
        self.scheduler.call_later(self.heartbeat_ms, self.heartbeat)

    def check_nodes(self):
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