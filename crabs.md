# ALP Signal MC Production with CRAB — Workflow Notes

## Overview

Full MC production chain for ALP signal samples (`gammaalp_0W1B_2jets`), running inside a Singularity container on the T2_US_UCSD cluster. Each step produces a DBS-published USER dataset that feeds into the next step.

**Chain:** GEN-SIM → DR step1 → DR step2 → MDSNANO

**Note:** Make sure your gridpacks are accessible via xrootd. Working on UCSD tier-2 (uaf) server, I moved my gridpacks to `/ceph/cms/store/group/LLPs/russelld/ALPs/gammaalp_0W1B_2jets_8dot6_GRIDPACKS/`.
---

## Environment Setup

Every time you open a new Singularity shell, you must re-initialize the CMSSW environment:

```bash
cd CMSSW_14_0_19/src
cmsenv
source /cvmfs/cms.cern.ch/crab3/crab.sh
```
I had to jump into a singularity container because of a `voms-myroxy` error. So, 
```bash
cd CMSSW_14_0_19/src
cmsenv
cmssw-el8
```
Once inside `singularity>`:
```bash
source /cvmfs/cms.cern.ch/cmsset_default.sh
cmsenv
source /cvmfs/cms.cern.ch/crab3/crab.sh
```

Forgetting `cmsenv` causes errors like:
```
ModuleNotFoundError: No module named 'past'
```

---

## Step 0: GEN-SIM

**Script:** `python3 LLPSignalGeneration/multi_crab_submit_step0.py`

**Check Status:** `crab status -d crab/gammaalp_0W1B_2jets_8dot6_ct_100` 
This directory was made when you submitted the job via `python3`.

### Key fix: XRootD URL format

The gridpack URL in the fragment pset must use the **global CMS XRootD redirector** with the correct double-slash syntax:

```python
# WRONG (causes ExternalLHEProducer child exit code 1)
args = cms.vstring('root:/cmsxrootd.fnal.gov//store/group/LLPs/...tarball.tar.xz'),

# CORRECT
args = cms.vstring('root://cms-xrd-global.cern.ch//store/group/LLPs/...tarball.tar.xz'),
```

Two issues in the original:
1. `root:/` (one slash) instead of `root://` (two slashes) — malformed URL
2. `cmsxrootd.fnal.gov` is a FNAL-local redirector; use `cms-xrd-global.cern.ch` for files at UCSD

### Verify the gridpack is staged before submitting

```bash
xrdfs cms-xrd-global.cern.ch locate /store/group/LLPs/russelld/ALPs/gammaalp_0W1B_2jets_8dot6_GRIDPACKS/llp_gen_gammaalp_8dot6_ct_100_el8_amd64_gcc10_CMSSW_13_0_13_tarball.tar.xz
```

### Event count

Controlled by `config.Data.unitsPerJob` (CRAB overrides `maxEvents` in the pset for `PrivateMC` splitting). The pset can keep `maxEvents = 10000`; CRAB sets the actual count.

### Output dataset example

```
/ALP_gammaalp_0W1B_2jets_8dot6_ct_100/LLPs-crab_Summer24_gammaalp_0W1B_2jets_8dot6_ct_100-4aaf545a278e22c2a9b29ecad65c49e4/USER
```

---

## Step 1: DR step1

**Script:** `python3 LLPSignalGeneration/multi_crab_submit_step1.py`

- Input: GEN-SIM output dataset (published to `phys03`)
- Splitting: `FileBased`, `unitsPerJob = 1`
- For a test with 1 GEN-SIM file: set `config.Data.totalUnits = 1`
- CRAB overrides `fileNames` and `maxEvents` in the pset automatically
- Uses 2 cores (`numberOfThreads = 2`) — the multi-core warning from CRAB is expected and safe to ignore if the pset is correctly configured

### Output dataset example

```
/ALP_gammaalp_0W1B_2jets_8dot6_ct_100/LLPs-crab_gammaalp_0W1B_2jets_8dot6_ct_100_Summer24_DRstep1_v2-48cd555cdf6be04e2ea7b276952e1164/USER
```

---

## Step 2: DR step2

**Script:** `python3 LLPSignalGeneration/multi_crab_submit_step2.py`

- Input: DR step1 output dataset
- `config.Data.inputDBS = 'phys03'` (USER dataset)
- 1 core, `maxMemoryMB = 3000`

### Output dataset example

```
/ALP_gammaalp_0W1B_2jets_8dot6_ct_100/LLPs-crab_gammaalp_0W1B_2jets_8dot6_ct_100_Summer24_DRstep2-89578c67bc58e175e14cb8efc9d9e047/USER
```

---

## Step 3: MDSNANO (NanoAOD + MDS tables)

**Script:** `python3 LLPSignalGeneration/multi_crab_submit_MDSNANO.py`

### Key difference from standard NanoAOD

The MDS (Multi-Detector Shower) custom tables must be added to the pset after `nanoAOD_customizeCommon`:

```python
process = nanoAOD_customizeCommon(process)
from HMTntuple.CSCShowerAnalyzer.custom_mds_cff import add_mdsTables
process = add_mdsTables(process, saveRechits=True)
```

### HMTntuple package requirement

`HMTntuple` is a custom CMSSW package not available in standard releases. It must be checked out and compiled separately. It was installed in **CMSSW_15_0_2** (not CMSSW_14_0_19):

```bash
cd CMSSW_15_0_2/src
# clone HMTntuple repo here
scram b -j8
cmsenv
source /cvmfs/cms.cern.ch/crab3/crab.sh
# then submit from this environment
python3 .../multi_crab_submit_MDSNANO.py
```

> **Note:** Submitting from CMSSW_15_0_2 means CRAB ships that release to the grid. The pset global tag (`150X_mcRun3_2024_realistic_v2`) was originally for CMSSW_14_X but works in practice.

## Chain the Above Steps via the CLI

I was getting issues with `nohup` failing because of gridpack, so I switched to `tmux`.
On the terminal 
```bash
tmux new -s crab_chain
cmsenv
cmssw-el8
voms-proxy-init --voms cms --valid 192:00
python3 LLPSignalGeneration/crab_chain_submit.py 2>&1 | tee chain.log # tee allows output to terminal, too
```
* This will start a `vim` like session. To detach, do `Ctrl+B, then D`. 
* To re-attach into the same session, do `tmux attach -t crab_chain`.
* To kill the session: `tmux kill-session -t crab_chain`.


### CRAB config notes

```python
config.Data.inputDBS = 'phys03'          # USER dataset from DR step2
config.Data.allowNonValidInputDataset = True
config.Data.ignoreLocality = True
config.Site.ignoreGlobalBlacklist = True
```

---

## Troubleshooting: Low Event Count in Output Files

### Symptom

After running the full chain, output files at every step (GEN-SIM, DR step1, DR step2, MDSNANO) contained only 1 event despite submitting 10. Checked with:

```bash
edmEventSize -v /ceph/cms/store/group/LLPs/.../file.root
# Output: Events 1
```

And in a notebook:
```python
print(events.event.compute())  # → [9]  (1 event, event number 9)
```

### Root Cause: Jet Matching Filter Efficiency

The event loss originated at **GEN-SIM** — not DR or NanoAOD. The `2jets` in the signal mode name means MLM jet matching is applied inside the gridpack. Not all generated LHE events pass the matching criteria. This is expected behavior for merged samples.

The matching efficiency was confirmed by retrieving the GEN-SIM job log:

```bash
crab getlog --short --jobids 1 -d crab/crab_Summer24_gammaalp_0W1B_2jets_8dot6_ct_100
```

In `results/job_out.1.0.txt`:

```
== CMSSW: Matching efficiency = 0.1 +/- 0.1   [TO BE USED IN MCM]
== CMSSW: Before matching: total cross section = 1.737e-06 +- 3.612e-08 pb
== CMSSW: After matching:  total cross section = 1.737e-07 +- 1.649e-07 pb
== CMSSW: After filter: final cross section = 1.737e-07 +- 1.649e-07 pb
```

**Matching efficiency ≈ 10%** → 1 out of 10 attempted events passed → 1 event in output. This is statistically consistent and not a bug.

### Production Scaling

To produce **N output events**, generate **N / matching_efficiency** attempted events:

```
target output events = 10,000
matching efficiency  = 0.10
→ total attempted    = 100,000
```

Example CRAB config for full production:
```python
config.Data.unitsPerJob = 1000   # attempted events per job
config.Data.totalUnits = 100000  # total attempted → ~10,000 output events
```

The large uncertainty on the efficiency (`0.1 +/- 0.1`) is purely due to 10-event statistics and will stabilize with more events.

---

## General CRAB Tips

- **Monitor jobs:** `crab status -d crab/<taskname>`
- **Verbose errors:** `crab status --verboseErrors -d crab/<taskname>`
- **Get logs:** `crab getlog -d crab/<taskname>`
- **Job state progression:** `submitted → running → transferring → finished`
- `transferring` is normal even for small jobs — file staging to T2_US_UCSD can take 10–30 minutes
- After fixing a config, delete the old task directory and resubmit (cannot `crab resubmit` with config changes for PrivateMC):
  ```bash
  rm -rf crab/crab_<taskname>
  ```
- `config.Data.inputDBS = 'phys03'` for all USER datasets; `'global'` only for official CMS datasets

---

## Site Configuration

```python
config.Site.storageSite = 'T2_US_UCSD'
config.Site.whitelist = ['T2_US_*', 'T3_US_FNALLPC']
config.Site.ignoreGlobalBlacklist = True
```

US-only whitelist keeps jobs close to storage at UCSD, reducing transfer times.