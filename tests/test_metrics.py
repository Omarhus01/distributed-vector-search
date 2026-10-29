from src.metrics import recall_at_k


def test_recall_matches_example_from_notes():
    # True top 3: a, b, c. Shard holding a and b is dead, so the system returns c, d, e.
    assert round(recall_at_k(["c", "d", "e"], ["a", "b", "c"]), 2) == 0.33


def test_recall_is_1_when_everything_is_found():
    assert recall_at_k(["b", "a", "c"], ["a", "b", "c"]) == 1.0