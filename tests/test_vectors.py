import json

import numpy as np

from src.vectors import euclidean, top_k


def test_distance_matches_hand_calculation():
    # Night Drive vs Neon Run: differences 0.05, 0.05, -0.05
    # 0.0025 + 0.0025 + 0.0025 = 0.0075, sqrt = 0.0866
    assert round(euclidean([0.80, 0.70, 0.10], [0.85, 0.75, 0.05]), 4) == 0.0866


def test_top_k_returns_closest_first():
    songs = {
        "Neon Run": [0.85, 0.75, 0.05],
        "City Lights": [0.70, 0.60, 0.20],
        "Sunday Coffee": [0.30, 0.40, 0.80],
        "Rainy Porch": [0.20, 0.30, 0.90],
    }
    result = top_k([0.80, 0.70, 0.10], songs, 2)
    assert [song_id for song_id, _ in result] == ["Neon Run", "City Lights"]


def test_ties_are_broken_by_song_id():
    # Two songs at the same distance: the smaller id comes first, every time.
    songs = {"b": [1.0, 0.0], "a": [0.0, 1.0]}
    result = top_k([0.0, 0.0], songs, 2)
    assert [song_id for song_id, _ in result] == ["a", "b"]


def test_ground_truth_matches_independent_numpy_version():
    # A second, separate way to compute the top-5. If top_k had a bug,
    # the ground truth would carry it too; numpy would not.
    songs = json.load(open("data/songs.json"))
    queries = json.load(open("data/queries.json"))
    ids = np.array([song["id"] for song in songs])
    vectors = np.array([song["vector"] for song in songs])

    for query in queries:
        distances = np.linalg.norm(vectors - np.array(query["vector"]), axis=1)
        order = np.lexsort((ids, distances))[:5]  # sort by distance, then id
        assert list(ids[order]) == [song_id for song_id, _ in query["true_top_k"]]