"""Simulated failures.

A crashed node is cut off from the network: every message to or from it is
dropped, which is what the rest of the cluster sees when a machine goes down.
"""
from dslabs import drop, partition


def crash(cluster, node_id):
    rule = partition({node_id})
    cluster.network.add_rule(rule)
    cluster.crashed[node_id] = rule
    cluster.scheduler.trace.note(node_id, "crashed")


def recover(cluster, node_id):
    cluster.network.remove_rule(cluster.crashed.pop(node_id))
    cluster.scheduler.trace.note(node_id, "recovered")

def slow_down(cluster, node_id, extra_ms):
    """Every message to or from node_id takes extra_ms longer. Returns the rule, to remove it later."""
    def rule(frm, to, deliveries, rng):
        if node_id in (frm, to):
            return [(delay + extra_ms, msg) for delay, msg in deliveries]
        return deliveries
    rule.__name__ = f"slow({node_id})"
    cluster.network.add_rule(rule)
    cluster.scheduler.trace.note(node_id, f"slowed down by {extra_ms} ms")
    return rule


def lose_messages(cluster, probability):
    """Every message in the cluster is lost with this probability. Returns the rule."""
    rule = drop(probability)
    cluster.network.add_rule(rule)
    cluster.scheduler.trace.note("c1", f"network loses {probability:.0%} of messages")
    return rule


def remove_fault(cluster, rule):
    cluster.network.remove_rule(rule)