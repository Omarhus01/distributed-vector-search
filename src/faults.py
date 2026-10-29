"""Simulated failures.

A crashed node is cut off from the network: every message to or from it is
dropped, which is what the rest of the cluster sees when a machine goes down.
"""
from dslabs import partition


def crash(cluster, node_id):
    rule = partition({node_id})
    cluster.network.add_rule(rule)
    cluster.crashed[node_id] = rule
    cluster.scheduler.trace.note(node_id, "crashed")


def recover(cluster, node_id):
    cluster.network.remove_rule(cluster.crashed.pop(node_id))
    cluster.scheduler.trace.note(node_id, "recovered")