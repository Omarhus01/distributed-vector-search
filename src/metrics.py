"""Search quality metrics."""


def recall_at_k(returned_ids, true_ids):
    """Return the share of the true top k that the system returned.

    Args:
        returned_ids: song ids the system returned.
        true_ids: song ids of the true top k.

    Returns:
        Number from 0 to 1. 1 means every true id was returned.
    """
    return len(set(returned_ids) & set(true_ids)) / len(true_ids)
