"""Distance and top-k search over song vectors.

The data script (ground truth) and the storage nodes both call these
functions, so they rank songs the same way.
"""
import math


def euclidean(a, b):
    """Return the Euclidean distance between two vectors of the same length."""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def top_k(query, songs, k):
    """Return the k songs closest to query.

    Compares the query to every song.

    Args:
        query: vector to search for.
        songs: dict of {song_id: vector}.
        k: number of songs to return.

    Returns:
        List of [song_id, distance], closest first. Songs at equal distance
        are ordered by song_id, so every node gives the same order.
    """
    scored = [(euclidean(query, vec), song_id) for song_id, vec in songs.items()]
    scored.sort()
    return [[song_id, dist] for dist, song_id in scored[:k]]