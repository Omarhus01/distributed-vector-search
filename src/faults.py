"""Simulated failures.

A crashed node is cut off from the network: every message to or from it is
dropped, which is what the other nodes see when a machine goes down.
A slow node has extra delay on its messages. A lossy network drops messages
at random.
"""
from dslabs import drop, partition


def crash(cluster, node_id):
    """Cut a node off from the network until recover is called.

    Args:
        cluster: the SimCluster.
        node_id: node to crash, such as "n2".
    """
    rule = partition({node_id})
    cluster.network.add_rule(rule)
    cluster.crashed[node_id] = rule
    cluster.scheduler.trace.note(node_id, "crashed")


def recover(cluster, node_id):
    """Reconnect a node that crash cut off."""
    cluster.network.remove_rule(cluster.crashed.pop(node_id))
    cluster.scheduler.trace.note(node_id, "recovered")

def slow_down(cluster, node_id, extra_ms):
    """Delay every message to or from a node.

    Args:
        cluster: the SimCluster.
        node_id: node to slow down.
        extra_ms: delay added to each message, in milliseconds.

    Returns:
        The network rule. Pass it to remove_fault to end the slowdown.
    """
    def rule(frm, to, deliveries, rng):
        if node_id in (frm, to):
            return [(delay + extra_ms, msg) for delay, msg in deliveries]
        return deliveries
    rule.__name__ = f"slow({node_id})"
    cluster.network.add_rule(rule)
    cluster.scheduler.trace.note(node_id, f"slowed down by {extra_ms} ms")
    return rule


def lose_messages(cluster, probability):
    """Drop each message in the cluster with the given probability.

    Args:
        cluster: the SimCluster.
        probability: chance of losing one message, from 0 to 1.

    Returns:
        The network rule. Pass it to remove_fault to end the loss.
    """
    rule = drop(probability)
    cluster.network.add_rule(rule)
    cluster.scheduler.trace.note("c1", f"network loses {probability:.0%} of messages")
    return rule


def remove_fault(cluster, rule):
    """Remove a rule returned by slow_down or lose_messages."""
    cluster.network.remove_rule(rule)