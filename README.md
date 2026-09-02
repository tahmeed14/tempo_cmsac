# "Tempo Control" - Carnegie Mellon Sports Analytics Conference 2026

Author: Tahmeed Tureen \<<tureen@umich.edu>\> \
Independent Football (Soccer) Analytics Researcher 

### Download Public Data

Gradient Sports (PFF FC) was kind enough to publicly release 64 matches worth of tracking and event data from the FIFA 2022 World Cup. We use these datasets.

You can download them from here: 

# Reproducible Pipeline

## Set Up Directories

From the repository root, create the required data directories:

```bash
python initiate_repository.py
```

## Run the Full Development Pipeline

Run the full pipeline from the repository root:

```bash
bash scripts/dev_full_pipeline.sh
```

The script runs the player lookup, event, tracking, integration, possession and tempo metric, and model-data pipelines in order. Pipeline
outputs are written to the standard directories under `data/curated`,
`data/staged`, `data/processed`, `data/integrated`, and `data/analysis`.


## Run the Pipeline for Selected Matches

There are a total of 64 matches. Pass one or more numeric match IDs to
the development script:

```bash
# One match
bash scripts/dev_one_match_pipeline.sh 3859

# Multiple matches processed as one combined investigation subset
bash scripts/dev_one_match_pipeline.sh 3859 3860 3861
```





## Development & Testing Environments

### MacOS

Specifications
SSD 512 GB
RAM 16 GB
Macbook Air M4

#### Computation Time
`pipeline_possessions.py`: 15 minutes, 41.937 seconds

### Linux Mint XCFE

### Windows

