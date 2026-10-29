# Distributed Vector Search

Find songs similar to a given song, with the songs spread across several nodes that can fail.

## How it works

Each song is a vector of five audio features: danceability, energy, acousticness, valence, and tempo.
Similar songs have vectors that are close together.
The songs are split into shards, and each shard lives on a storage node.
A coordinator sends a query to every shard, collects each shard's closest matches, and merges them into one answer.
The coordinator pings every node every 500 ms. A node silent for 1 s is suspected, and after 2 s it is marked dead and no longer asked.
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

On Windows, also run `$env:PYTHONUTF8 = "1"` in the terminal first, since dslabs reads its viewer file as UTF-8.

## Data

Download `dataset.csv` from the [Spotify Tracks Dataset](https://huggingface.co/datasets/maharshipandya/spotify-tracks-dataset) (Files and versions tab) and put it at `data/raw/dataset.csv`.
Then run:

```bash
python -m scripts.prepare_data
```

This writes `data/songs.json`, the songs in the cluster, and `data/queries.json`, the test songs with their true nearest neighbours.

## Quick start

```bash
python -m scripts.run_queries
```

This builds a cluster of one coordinator and three storage nodes, runs the 20 test queries, and prints recall@5, the share of the true top 5 the cluster returned.
It also writes `results/first_run.html`: open it in a browser and press Play to watch each query go out to the nodes and the answers come back.

To run the tests:

```bash
python -m pytest
```

## Breaking it

```bash
python -m scripts.run_crash
```

This runs the 20 test queries three times: with all nodes up, with n2 crashed, and after n2 recovers, and prints recall@5 for each.
A crash cuts the node off from the network, so every message to or from it is dropped.
The coordinator notices through missed heartbeats, and once n2 is marked dead its shard is skipped instead of waited for.
Open `results/crash_n2.html` to watch it: dropped messages end in a red cross, and status changes appear on c1's timeline.

## How it fits together

| Where | What |
|---|---|
| `scripts/prepare_data.py` | Raw CSV to song vectors, test queries, and ground truth |
| `scripts/run_queries.py` | Runs the test queries through the cluster and measures recall |
| `scripts/run_crash.py` | Crashes n2 mid-run and measures recall before, during, and after |
| `src/vectors.py` | Distance and brute-force top-k, used by everything that ranks songs |
| `src/storage_node.py` | `StorageNode`: holds shards, answers searches with its local top-k |
| `src/coordinator.py` | `Coordinator`: sends a query to every shard, merges the replies, times out on silent shards, tracks which nodes are alive with heartbeats |
| `src/cluster_setup.py` | Builds the cluster and splits the songs into shards |
| `src/faults.py` | `crash()` and `recover()` for the simulated cluster |
| `src/metrics.py` | recall@k |
| `tests/` | Tests for each of the above |