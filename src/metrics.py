def recall_at_k(returned_ids, true_ids):
    """Share of the true top-k that the system actually returned (1.0 = all of them)."""
    return len(set(returned_ids) & set(true_ids)) / len(true_ids)
