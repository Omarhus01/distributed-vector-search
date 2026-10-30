"""Turn the raw Spotify CSV into song vectors, test queries and ground truth.

Input:  data/raw/dataset.csv   (Spotify Tracks Dataset by maharshipandya, Hugging Face)
Output: data/songs.json        the songs that go into the cluster
        data/queries.json      test songs (not in the cluster) + their true top-k

Run from the repo root:  python -m scripts.prepare_data
"""

import json
from pathlib import Path

import pandas as pd

from src.similarity import top_k

RAW_CSV = Path("data/raw/dataset.csv")
SONGS_OUT = Path("data/songs.json")
QUERIES_OUT = Path("data/queries.json")

FEATURES = ["danceability", "energy", "acousticness", "valence", "tempo"]
N_SONGS = 1000      # songs in the cluster (small on purpose, so the viewer stays readable)
N_QUERIES = 20      # test songs, kept out of the cluster so a query never finds itself
K = 5
SEED = 42           # same seed = same sample every run

def load_and_clean(path):
    tracks = pd.read_csv(path)
    tracks = tracks.dropna(subset=["track_name", "artists"])
    # A song listed under several genres appears once per genre. Keep one row per song.
    tracks = tracks.drop_duplicates(subset="track_id")
    return tracks


def normalize(tracks):
    # Min-max scaling: each feature becomes 0..1.
    # Without this, tempo (0..243) would outweigh the other features (0..1).
    for feature in FEATURES:
        lowest, highest = tracks[feature].min(), tracks[feature].max()
        tracks[feature] = (tracks[feature] - lowest) / (highest - lowest)
    return tracks

def to_record(track):
    return {
        "id": track["track_id"],
        "name": track["track_name"],
        "artist": track["artists"],
        "genre": track["track_genre"],
        # Rounded so the vectors in the JSON are exactly the ones used for ground truth.
        "vector": [round(float(track[feature]), 6) for feature in FEATURES],
    }

def main():
    tracks = normalize(load_and_clean(RAW_CSV))
    print(f"{len(tracks)} unique songs after cleaning")

    picked = tracks.sample(n=N_SONGS + N_QUERIES, random_state=SEED)
    songs = [to_record(track) for _, track in picked.iloc[:N_SONGS].iterrows()]
    queries = [to_record(track) for _, track in picked.iloc[N_SONGS:].iterrows()]

    # Ground truth: brute force over all songs on one machine, nothing distributed.
    all_vectors = {song["id"]: song["vector"] for song in songs}
    for query in queries:
        query["true_top_k"] = top_k(query["vector"], all_vectors, K)

    SONGS_OUT.write_text(json.dumps(songs, indent=1))
    QUERIES_OUT.write_text(json.dumps(queries, indent=1))
    print(f"wrote {len(songs)} songs to {SONGS_OUT}")
    print(f"wrote {len(queries)} queries with true top-{K} to {QUERIES_OUT}")

    # One example to check by hand.
    query = queries[0]
    nearest_id, nearest_distance = query["true_top_k"][0]
    nearest = next(song for song in songs if song["id"] == nearest_id)
    print("\nCheck by hand:")
    print(f"  query   {query['name']} by {query['artist']}: {query['vector']}")
    print(f"  nearest {nearest['name']} by {nearest['artist']}: {nearest['vector']}")
    print(f"  distance = {nearest_distance:.4f}")


if __name__ == "__main__":
    main()