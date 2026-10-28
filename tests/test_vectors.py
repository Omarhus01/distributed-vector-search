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