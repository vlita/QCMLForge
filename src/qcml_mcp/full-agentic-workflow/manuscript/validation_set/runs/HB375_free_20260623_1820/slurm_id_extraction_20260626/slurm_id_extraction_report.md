# Slurm ID Extraction Report

Input reset records: `/home/vlita3/QCMLForge/src/qcml_mcp/full-agentic-workflow/manuscript/validation_set/runs/HB375_free_20260623_1820/reset_failed_20260624_0905/reset_record_ids.csv`

Detailed search output: `/home/vlita3/QCMLForge/src/qcml_mcp/full-agentic-workflow/manuscript/validation_set/runs/HB375_free_20260623_1820/slurm_id_extraction_20260626/reset_records_error_history_scheduler_search.csv`

Slurm/job-id candidate output: `/home/vlita3/QCMLForge/src/qcml_mcp/full-agentic-workflow/manuscript/validation_set/runs/HB375_free_20260623_1820/slurm_id_extraction_20260626/slurm_job_id_candidates.csv`

## Result

No Slurm job IDs, `SLURM_JOB_ID` values, `sbatch` IDs, `sacct` IDs, or generic scheduler job-id candidates were found in QCFractal compute histories, provenance, manager names, or stored error output for the 905 reset HB375 manybody records.

## Evidence

- Reset manybody records checked: 905
- Error-history rows inspected: 3326
- Failed child singlepoint histories inspected: 2421
- Manybody-level error histories inspected: 905
- `FileNotFoundError` child histories: 2421
- `service_iteration_error` manybody histories: 905
- Rows with Parsl traceback text: 2421
- Rows with Slurm/job-id candidates: 0

## Manager Names Present

```json
{
  "phoenix-login-phoenix-gnr-2.pace.gatech.edu-a7a82092-65f2-4340-beed-87bd4d98b90c": 2421,
  "NaN": 905
}
```

## Interpretation

QCFractal retained the QCFractal compute manager name and the Python/Parsl exception payload, but not the Slurm allocation or Slurm job ID. The failed attempts point to manager `phoenix-login-phoenix-gnr-2.pace.gatech.edu-a7a82092-65f2-4340-beed-87bd4d98b90c`, which is a QCFractal compute manager identity, not a Slurm job number.

To recover actual Slurm job IDs, inspect Phoenix-side compute-manager/Parsl logs or Slurm accounting (`sacct`) for the failed history time window.
