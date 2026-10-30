"""Distance and top-k search, shared by the data script and the storage nodes.

Everything that ranks songs uses these two functions, so the ground truth
and the cluster can never disagree about what "closest" means.
"""
import math


def euclidean(a, b):
    """Straight-line distance between two vectors of the same length."""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def top_k(query, songs, k):
    """Brute force: compare the query to every song, return the k closest.

    songs: dict of {song_id: vector}
    Returns a list of [song_id, distance], closest first.
    Ties on distance are broken by song_id, so every node orders them the same way.
    """
    scored = [(euclidean(query, vec), song_id) for song_id, vec in songs.items()]
    scored.sort()
    return [[song_id, dist] for dist, song_id in scored[:k]]