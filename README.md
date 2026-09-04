# "Tempo Control" — Carnegie Mellon Sports Analytics Conference 2026

Author: Tahmeed Tureen \<<tureen@umich.edu>\> \
Independent Football (Soccer) Analytics Researcher

## Download the public data

This project uses the 64-match FIFA 2022 World Cup dataset released publicly
by Gradient Sports (PFF FC). Gradient Sports does not provide an API for this
dataset, so the files must be downloaded and placed in the repository manually.

Download the dataset from the
[Gradient Sports Google Drive folder](https://drive.google.com/drive/folders/1_a_q1e9CXeEPJ3GdCv_3-rNO3gPqacfa).

The download contains four data types. Copy the files for each type into the
matching repository directory:

| Downloaded data type | Required destination |
|---|---|
| `events` | `data/raw/gradient_sports/events/` |
| `tracking` | `data/raw/gradient_sports/tracking/` |
| `metadata` | `data/raw/gradient_sports/metadata/` |
| `roster` | `data/raw/gradient_sports/roster/` |

The directory names and downloaded filenames must match exactly. Do not rename
the data-type folders or source files. In particular, use lowercase directory
names as shown above and preserve these file patterns:

- Events: `<match_id>.json`
- Tracking: `<match_id>.jsonl.bz2`
- Metadata: `<match_id>.json`
- Rosters: `<match_id>.json`

For example, the event file for match `10517` must be located at
`data/raw/gradient_sports/events/10517.json`.

## Reproducible pipeline

### Set up directories

Before copying the downloaded data, run the repository initializer from the
repository root:

```bash
python initiate_repository.py
```

This creates all required directories but does not download any data. After it
finishes, copy the downloaded files into the destinations listed above.

### Run the full development pipeline

Run the full pipeline from the repository root:

```bash
bash scripts/dev_full_pipeline.sh
```

The script runs the player lookup, event, tracking, integration, possession and
tempo-metric, and model-data pipelines in order. Pipeline outputs are written
to the standard directories under `data/curated`, `data/staged`,
`data/processed`, `data/integrated`, and `data/analysis`.

### Run the pipeline for selected matches

There are a total of 64 matches. Pass one or more numeric match IDs to
the development script:

```bash
# One match
bash scripts/dev_one_match_pipeline.sh 3859

# Multiple matches processed as one combined investigation subset
bash scripts/dev_one_match_pipeline.sh 3859 3860 3861
```

## Development and testing environments

### macOS

Specifications:

- SSD: 512 GB
- RAM: 16 GB
- MacBook Air M4

#### Computation time

`pipeline_possessions.py`: 15 minutes, 41.937 seconds

### Linux Mint XFCE

### Windows
