---
name: full-agentic-workflow
description: >-
  Use this skill when the user explicitly asks for "full-agentic-workflow".
  This skill runs an end-to-end quantum chemistry pipeline: (1) recommend a level of theory (LoT) via select-LoT given a geometry directory and compute budget,
  (2) start or verify a local QCFractal instance, (3) queue manybody computations on ALL budget-feasible LoTs and retrieve results,
  (4) convert interaction energies to kcal/mol, and (5) compute signed errors against a user-provided reference.
  The pipeline uses two conda environments: qcml for select-LoT, and p4_qcml for QCFractal operations.
---

# full-agentic-workflow

End-to-end quantum chemistry workflow that chains together three sub-skills:
1. **select-LoT** — predict IE errors and timings, filter by budget, recommend best LoT
2. **connect-qcf** — start/verify a local QCFractal instance
3. **run-IEs** — queue and retrieve manybody interaction energies for ALL budget-feasible LoTs
4. **Post-process** — convert to kcal/mol, flip sign, compute signed errors vs reference

## When to use

Only trigger this skill when the user explicitly says `full-agentic-workflow`.

## Environment requirements

This workflow requires **two conda environments**. You must switch between them at the right phases:

| Phase | Environment | Reason |
|-------|-------------|--------|
| select-LoT (parsing, prediction) | `qcml` | Needs `psi4`, `apnet_pt`, `qcml_mcp` with pretrained models |
| connect-qcf, run-IEs, post-processing | `p4_qcml` | Needs `qcportal`, `qcfractal`, `pandas`, `psi4`, `qcmanybody` |

### Conda activation in subprocesses

`conda activate` does not work in OpenCode's non-interactive shell. Do not use `conda activate <env>` — it will fail with `CondaError: Run 'conda init' before 'conda activate'`. Instead, invoke Python directly using the env's full binary path:

- qcml: `/home/vlita3/miniconda3/envs/qcml/bin/python3`
- p4_qcml: `/home/vlita3/miniconda3/envs/p4_qcml/bin/python3`

Confirm which environment is active by checking `sys.executable`.

### Cross-environment data transfer

The two conda environments use different Python versions (qcml = 3.12, p4_qcml = 3.10) with the same qcelemental version (0.29.0) but different internal module structures. **Do not pickle DataFrames containing qcelemental Molecule objects in one env then load them in the other** — it will fail with `ModuleNotFoundError: No module named 'qcelemental.models.v1'`.

To transfer data across environments, save geometry file paths instead of pickled molecule objects. Both envs can parse the same geometry files directly.

## Inputs you must collect

- **Geometry directory**: Path to a directory of dimer geometry files accepted by `src/qcml_mcp/ie_time_esimator_script.py`.
- **Compute budget**: Walltime in seconds (not CPU-seconds).
- **Reference energies**: Interaction energies provided by the user in any format (CSV, text, dataframe, screenshot). The model is responsible for parsing these into a usable format.
- **Optional**: List of QM methods and basis sets. Defaults to all 10 methods and 6 basis sets if not specified.
- **Optional**: Counterpoise correction (`using_cp`). Defaults to True. When True, the IE predictions use CP-corrected models. Note this affects the interaction energies, not the timing model.

## Phase 1: select-LoT (qcml environment)

Use the qcml Python binary: `/home/vlita3/miniconda3/envs/qcml/bin/python3`.

### Step 1: Build the prediction dataframe

Call `src/qcml_mcp/ie_time_esimator_script.py`'s `main()` function:
```python
from qcml_mcp.ie_time_esimator_script import main

df = main(
    geom_path=<geometry_directory>,
    methods=<methods or None>,
    bases=<bases or None>,
    auto_download=True,
)
```

This returns a dataframe with columns including:
- `id` — system identifier
- `qcel_dimer` — QCElemental Molecule for each dimer
- `qcel_monA`, `qcel_monB` — monomer molecules
- `Level of Theory` — e.g., "HF/cc-pVDZ/unCP"
- `ERROR ESTIMATES (kcal/mol)` — predicted IE error vs CCSD(T)/CBS
- `ESTIMATED CPU TIMES (log10(s))` — predicted CPU time

### Step 2: Save the full dataframe

Save to `select_lot_df.pkl` in the current working directory.

### Step 3: Filter by budget

Convert timing to walltime seconds:
```python
df["walltime_seconds"] = 10 ** df["ESTIMATED CPU TIMES (log10(s))"]
```

Filter to rows where `walltime_seconds <= <user_budget>`. If no rows remain, report that no LoT fits the budget and wait for user input.

### Step 4: Recommend the best LoT

For each system (group by `id`), find the LoT with the minimum absolute error among budget-feasible rows. Count how many systems each LoT wins. Choose the LoT with the largest count.

Tie-breakers: lowest median absolute error, then lowest median walltime.

This recommendation is informational — it tells the user which LoT is predicted to be best. All LoTs proceed to computation.

### Step 5: Build the submission dataframe

The full dataframe (all systems × all LoTs) is the submission dataframe. It already contains all needed data. However, **do not include qcelemental Molecule objects** — they will not survive the environment switch. Instead:

1. Create a separate `geom_index.csv` mapping system `id` to its original geometry file path in the user-provided directory.
2. Save the submission dataframe with all columns EXCEPT `qcel_dimer`, `qcel_monA`, `qcel_monB` columns (drop the molecule objects).
3. Save both files — they will be recombined in Phase 3.

```python
# Save geometry file index
import pandas as pd, os

geom_dir = <geometry_directory>
geom_index = pd.DataFrame({
    "id": df["id"].unique(),
    "geom_path": [os.path.join(geom_dir, f) for f in os.listdir(geom_dir) if os.path.isfile(os.path.join(geom_dir, f))]
})
# Match file extensions — use the actual file names from the geometry directory
# that correspond to each system id
geom_index.to_csv("geom_index.csv", index=False)

# Drop molecule columns, save submission df
sub_df = df.drop(columns=["qcel_dimer", "qcel_monA", "qcel_monB"], errors="ignore")
sub_df.to_pickle("run_ies_input.pkl", protocol=2)
```

If the user wants to run only a specific subset of LoTs (e.g., just the recommended one), ask them to confirm. By default, **all LoTs** are submitted.

## Phase 2: connect-qcf (p4_qcml environment)

Use the p4_qcml Python binary: `/home/vlita3/miniconda3/envs/p4_qcml/bin/python3`.

Follow the `connect-qcf` skill workflow:
1. Ensure `QCF_BASE_FOLDER` is set. If not, ask the user.
2. Check if a QCFractal instance already exists at `$QCF_BASE_FOLDER`.
3. If it exists but is inactive, start server and compute manager in background.
4. If no setup exists, initialize using `src/qcmlforge/qca.py` conventions (port 7777, no security). Ensure the following resource config is used (not the default values):
```
    resources_config={
        "update_frequency": 15,
        "cores_per_worker": 10,
        "max_workers": 1,
        "memory_per_worker": 250,
    },
```
5. Verify with both process checks (`pgrep`) and `qcportal.PortalClient` connectivity.

Do not proceed to Phase 3 until the QCFractal instance is confirmed active and reachable.

## Phase 3: run-IEs (p4_qcml environment)

Still in the `p4_qcml` environment.

### Step 1: Load and attach molecule objects from geometry files

The submission dataframe was saved without molecule objects (they don't survive env switching). Reconstruct them by re-parsing the original geometry files:

```python
import pandas as pd
import qcelemental as qcel

df = pd.read_pickle("run_ies_input.pkl")
geom_index = pd.read_csv("geom_index.csv")

# Parse geometry files to reconstruct molecule objects
def get_qcel_dimer(geom_path):
    with open(geom_path, "r") as f:
        raw = f.read()
    return qcel.models.Molecule.from_data(raw)

mol_map = {}
for _, row in geom_index.iterrows():
    mol_map[row["id"]] = get_qcel_dimer(row["geom_path"])

# Attach molecule objects to the submission dataframe
df["qcel_dimer"] = df["id"].map(mol_map)
```

### Step 2: Queue manybody computations

```python
from qcml_mcp.run_IEs.example_manybody import queue_manybodys

df = queue_manybodys(df)
```

### Step 3: Confirm and exit

Use `check_manybody_progress(df)` to verify records entered `waiting` or `running` state. Note the following:

- How many jobs were submitted
- For each job, the predicted walltime vs the user's budget
- The predicted completion time window based on the estimated timings

Then **stop execution and report to the user**. Do not poll. These jobs take hours or days.

### Step 4: User re-queries for status

When the user asks about progress (e.g., "are my jobs done?", "check status"):

1. Load `run_ies_queued.pkl`.
2. Call `check_manybody_progress(df)` to get current status.
3. For still-running jobs, compute a **predicted completion percentage**:
   ```python
   # elapsed_since_submission = current_time - submission_time
   # predicted_walltime_seconds = 10 ** df["ESTIMATED CPU TIMES (log10(s))"]
   # completion_pct = min(100 * elapsed_since_submission / predicted_walltime, 99)
   ```
4. Report status per job (waiting/running/complete/error) with completion percentages.
5. If any jobs completed early or errored, note that.
6. **Exit**. Do not call `retrieve_manybodies()` until all jobs are complete.

### Step 5: All jobs complete — retrieve results

When status checks show all records are `complete` (or errored):

1. Call `retrieve_manybodies(df)` once.
2. Report count of completed vs errored jobs.
3. Save as `run_ies_results.pkl`.

## Phase 4: Post-processing

Still in the `p4_qcml` environment.

### Step 1: Parse reference energies

The user provides reference interaction energies. The reference must contain at minimum system identifiers (matching the `id` column) and the reference interaction energy in kcal/mol.

Normalize the reference into a Series or DataFrame keyed by system `id`.

### Step 2: Extract the interaction energy

The `retrieve_manybodies()` function in `example_manybody.py` searches for the IE using several key patterns. However, if it returns `NaN`, inspect the record properties directly. The IE may be nested under `properties['results']['cp_corrected_interaction_energy']` (for CP-corrected) or `properties['results']['nocp_corrected_interaction_energy']` (for non-CP). Inspect the record with `rec.properties` to find the actual key.

If you need to extract it manually:
```python
client = qcportal.PortalClient("http://localhost:7777", verify=False)
records = client.get_manybodys([qcf_id], include=["clusters", "**"])
rec = records[0]
props = rec.properties
# Inspect props to find the IE key, e.g.:
# props['results']['cp_corrected_interaction_energy']
```

### Step 3: Convert manybody energies to kcal/mol
```python
from apnet_pt.constants import h2kcalmol
h2kcalmol = 627.509  # hartree to kcal/mol

df["mb_ie_kcalmol"] = df["mb_interaction_energy"] * h2kcalmol
```

Do not flip the sign of the QCFractal computed energies — keep them as-is from the server.

### Step 4: Flip sign of select-LoT predictions

The `ERROR ESTIMATES (kcal/mol)` column from select-LoT uses a sign convention that requires flipping:
```python
df["ERROR ESTIMATES (kcal/mol)"] = -df["ERROR ESTIMATES (kcal/mol)"]
```

### Step 5: Compute signed errors

Merge the reference energies with the results dataframe on `id`. Compute signed errors:
```python
df["IE_error_kcalmol"] = df["mb_ie_kcalmol"] - df["reference_ie"]
```
Round the final value so that it has the same number of decimal places as the least precise value in the subtraction. 

Positive error means the predicted binding is weaker than reference (underbinding). Negative means overbinding.

### Step 6: Save the final dataframe

Save as `full_workflow_results.pkl`. Include at minimum: `id`, `Level of Theory`, `mb_interaction_energy`, `mb_ie_kcalmol`, `reference_ie`, `IE_error_kcalmol`, `walltime_seconds`.

## Output requirements

Always provide:

1. **Printed report** including:
   - The recommended LoT from Phase 1
   - Budget used and how many LoTs were feasible
   - QCFractal connection status
   - Number of manybody jobs submitted (total across all systems × LoTs)
   - On re-query: predicted completion percentages per job
   - After completion: completed vs errored counts
   - Summary statistics of errors vs reference (mean, median, max, min signed error)
   - A short table of per-system errors for the recommended LoT

2. **Saved files**:
   - `select_lot_df.pkl` — full select-LoT prediction dataframe
   - `run_ies_input.pkl` — submission dataframe (all feasible LoTs)
   - `run_ies_queued.pkl` — queued dataframe with QCFractal IDs
   - `run_ies_results.pkl` — raw results from QCFractal
   - `full_workflow_results.pkl` — final dataframe with energies in kcal/mol and errors

## Execution model

This workflow is **not** a single continuous execution. It spans multiple user interactions:

1. **First invocation**: Run Phase 1 → Phase 2 → Phase 3 (submit only, then exit).
2. **Subsequent re-queries**: Run Phase 3 Step 4 (status check, report, exit).
3. **Final invocation**: When jobs are complete, run Phase 3 Step 5 + Phase 4 (retrieve, post-process, report).

Each interaction should save intermediate files so state persists across sessions.

## Error handling

### Environment errors
If a command fails with `ModuleNotFoundError`, `ImportError`, or `conda` errors:
1. Check which environment is active.
2. Verify the environment has the required packages.
3. Report the missing package and suggest installation.
4. Do not blindly edit source code.

### QCFractal errors
If connection to QCFractal fails:
1. Confirm `QCF_BASE_FOLDER` is set.
2. Check if the server process is running.
3. Check `$QCF_BASE_FOLDER/logs/` for error messages.
4. Report findings to the user.

### Computation errors
If manybody jobs error out:
1. Report the error details from the QCFractal record.
2. Ask the user whether to troubleshoot or proceed with partial results.

## Skill interaction notes

- This skill does NOT modify or replace the three sub-skills. It orchestrates them.
- When calling code from `select-LoT` or `run-IEs` sub-skill scripts, import from the canonical module paths:
  - `qcml_mcp.ie_time_esimator_script`
  - `qcml_mcp.run_IEs.example_manybody`
  - `qcmlforge.qca` (for QCFractal setup)
