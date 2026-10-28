# Distributed Vector Search

Find songs similar to a given song, with the songs spread across several nodes that can fail.

## How it works

Each song is a vector of five audio features: danceability, energy, acousticness, valence, and tempo.
Similar songs have vectors that are close together.
The songs are split into shards, and each shard lives on a storage node.
A coordinator sends a query to every shard, collects each shard's closest matches, and merges them into one answer.
Each shard has a replica on another node, so the system keeps answering when a node fails.

The cluster runs on [dslabs](https://github.com/cscheffler/dslabs), the course's deterministic simulator, so every failure can be replayed and watched.

## Install

Requires Python 3.10 or newer.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Mac/Linux
pip install -r requirements.txt
```

## Data

Download `dataset.csv` from the [Spotify Tracks Dataset](https://huggingface.co/datasets/maharshipandya/spotify-tracks-dataset) (Files and versions tab) and put it at `data/raw/dataset.csv`.
Then run:

```bash
python -m scripts.prepare_data
```

This writes `data/songs.json`, the songs in the cluster, and `data/queries.json`, the test songs with their true nearest neighbours.