# ALP Signal MC Production: Full-Scale CRAB Chain Setup

## Overview

Automated chain: **GEN-SIM → DR step1 → DR step2 → MDSNANO**

Each step is submitted automatically once the previous step completes. The chain is driven by `LLPSignalGeneration/crab_chain_submit.py`, run from `CMSSW_14_0_19/src`. MDSNANO is submitted via a bash wrapper that switches to the `CMSSW_15_0_2` environment (required for HMTntuple).

---

## Prerequisites

- CMSSW_14_0_19 compiled with LLPSignalGeneration package
- CMSSW_15_0_2 compiled with HMTntuple/LLPSignalGeneration
- Valid VOMS proxy (`voms-proxy-init --voms cms`)
- Run everything inside a `tmux` session (keeps the process alive and preserves the TTY needed for VOMS)

```bash
tmux new -s chain
cd /home/users/russelld/ALPs/work/cmssw/CMSSW_14_0_19/src
cmsenv
cmssw-el8
cmsenv
source /cvmfs/cms.cern.ch/crab3/crab.sh
```

---

## Key Files

| File | Purpose |
|------|---------|
| `LLPSignalGeneration/crab_chain_submit.py` | Main chain script |
| `LLPSignalGeneration/submit_mdsnano_wrapper.sh` | Switches to CMSSW_15_0_2 and calls CLI |
| `LLPSignalGeneration/submit_mdsnano_cli.py` (CMSSW_14_0_19) | Reference copy |
| `LLPSignalGeneration/submit_mdsnano_cli.py` (CMSSW_15_0_2) | **Active copy** used by wrapper |

---

## Step-by-Step Setup for a New Production Campaign

### 1. Set event counts

In `crab_chain_submit.py`, under `USER SETTINGS`:

```python
GENSIM_EVENTS_PER_JOB = 1000    # attempted events per job
GENSIM_TOTAL_EVENTS   = 100000  # 100 jobs → ~10k passing (10% MLM filter efficiency)

DR1_UNITS_PER_JOB = 1
DR1_TOTAL_UNITS   = -1  # -1 = process all files in the dataset

DR2_UNITS_PER_JOB = 1
DR2_TOTAL_UNITS   = -1

NANO_UNITS_PER_JOB = 1
NANO_TOTAL_UNITS   = -1  # note: actual value set in submit_mdsnano_cli.py
```

Also set `totalUnits = -1` directly in **both** copies of `submit_mdsnano_cli.py` since `NANO_TOTAL_UNITS` is not passed through:

```python
config.Data.totalUnits = -1
```

### 2. Set a new work area

Change `CRAB_WORK_AREA` to a fresh directory name to avoid conflicts with previous runs. CRAB will create all task subdirectories inside it.

In `crab_chain_submit.py`:

```python
CRAB_WORK_AREA = 'crab_10k'
```

Also update the matching variable in **both** copies of `submit_mdsnano_cli.py`:

```python
CRAB_WORK_AREA = "crab_10k"
config.General.workArea = f"/home/users/russelld/ALPs/work/cmssw/CMSSW_14_0_19/src/{CRAB_WORK_AREA}"
```

### 3. Bump request names

Each unique `requestName` produces a unique DBS dataset path, ensuring no stale/deleted files from previous runs appear in the new dataset. Update the name in each `submit_step*` function and both CLI copies. The `task_dir` must always follow the pattern `{CRAB_WORK_AREA}/crab_{requestName}` — CRAB prepends `crab_` to the request name when creating the local directory.

```python
# GEN-SIM (submit_step0)
config.General.requestName = f'10k_Summer24_v3_{GAMMAALP_MODE}'
task_dir = f"{CRAB_WORK_AREA}/crab_10k_Summer24_v3_{GAMMAALP_MODE}"

# DR step1 (submit_step1)
request_name = f'10k_{GAMMAALP_MODE}_{CAMPAIGN}_DRstep1_v3'
task_dir     = f"{CRAB_WORK_AREA}/crab_{request_name}"

# DR step2 (submit_step2)
request_name = f'10k_{GAMMAALP_MODE}_{CAMPAIGN}_DRstep2_v2'
task_dir     = f"{CRAB_WORK_AREA}/crab_{request_name}"

# MDSNANO (submit_mdsnano in chain script + both CLI copies)
request_name = '10k_' + dr2_dataset.split('/')[1] + '_v2'
task_dir     = f"{CRAB_WORK_AREA}/crab_{request_name}"
```

### 4. Clear resume variables

```python
RESUME_GENSIM_DATASET = ""
RESUME_DR1_DATASET    = ""
RESUME_DR2_DATASET    = ""
```

### 5. Disable block filtering

```python
USE_INPUT_BLOCKS = False
```

Block filtering is only needed when resuming from a polluted dataset (see below).

### 6. Run the chain

```bash
python3 LLPSignalGeneration/crab_chain_submit.py 2>&1 | tee chain_10k.log
```

---

## Design Notes

### DBS publication lag

CRAB marks a task `COMPLETED` before files are fully registered in DBS or accessible via XRootD. The script handles this with `wait_for_dbs_dataset()`, which polls `dasgoclient` and verifies XRootD accessibility before submitting the next step.

### Random seeds

No manual seed management is needed. CRAB assigns each `PrivateMC` job a unique luminosity block number, and CMSSW's `RandomNumberGeneratorService` automatically derives different seeds per lumi block — even when `initialSeed` is hardcoded in the pset.

### `submit_mdsnano_wrapper.sh` — `set --` fix

`source /cvmfs/cms.cern.ch/crab3/crab.sh` inherits the shell's positional parameters. Without clearing them first, `crab.sh` sees `$1` as the dataset path and rejects it as an invalid CRAB environment type. The wrapper must always include:

```bash
set --
source /cvmfs/cms.cern.ch/crab3/crab.sh
```

---

## Resuming a Partial Chain

If the chain crashes after some steps complete, set the known-good dataset paths to skip those steps on restart:

```python
RESUME_GENSIM_DATASET = "/ALP_.../USER"  # set to skip GEN-SIM
RESUME_DR1_DATASET    = "/ALP_.../USER"  # set to skip DR step1
RESUME_DR2_DATASET    = "/ALP_.../USER"  # set to skip DR step2
```

If resuming into a **polluted dataset** (files were deleted from disk but remain in DBS), also enable block filtering:

```python
USE_INPUT_BLOCKS = True
```

This restricts each downstream step to only the DBS blocks containing XRootD-accessible files, preventing CRAB from picking a dead file.

> **Important:** Never delete output files from a previous production version. Deleting files from disk does **not** remove them from DBS — stale entries remain permanently and cause downstream jobs to fail.
