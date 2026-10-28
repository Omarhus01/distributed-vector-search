# Distributed Vector Search

A distributed similarity search over Spotify songs: "find songs like this one", with the songs split across several nodes, replicated, and kept available when nodes fail.

Built on [dslabs](https://github.com/cscheffler/dslabs), the course's distributed-systems simulator, for IL18105 (Distributed Systems, Minerva University, Fall 2026).

## Status

Work in progress. See `docs/decisions.md` for design decisions so far.

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Data

1. Download `dataset.csv` from the [Spotify Tracks Dataset](https://huggingface.co/datasets/maharshipandya/spotify-tracks-dataset) (Files and versions tab).
2. Put it at `data/raw/dataset.csv` (this folder is not committed).
3. Run:

```bash
python -m scripts.prepare_data
```

This writes `data/songs.json` (songs in the cluster) and `data/queries.json` (test songs and their true nearest neighbours).

## Repo layout

| Path | What |
|---|---|
| `scripts/prepare_data.py` | Raw CSV to song vectors, test queries and ground truth |
| `src/vectors.py` | Distance and brute-force top-k, shared by everything |
| `src/` | The nodes (in progress) |
| `notebooks/` | Demo (in progress) |
| `docs/decisions.md` | Design decisions and why |
