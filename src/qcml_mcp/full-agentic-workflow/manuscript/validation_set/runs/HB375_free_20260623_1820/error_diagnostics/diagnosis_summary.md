# HB375 Failure Diagnosis Summary

## Conclusion

The failed HB375 records appear to be infrastructure/compute-manager failures, not Psi4 input or chemistry failures.

The error pattern is consistent with worker interruption, preemption, or scratch/temp-file cleanup while the QCFractal compute manager was collecting task results from Phoenix `free` queue jobs.

## Evidence

- All 905 failed manybody records have the same top-level error:
  - `service_iteration_error: Some task(s) did not complete successfully`
- Sampled failed child singlepoints all fail with manager-side `FileNotFoundError` while retrieving task results.
- The full sampled payload in `full_first_error_payload.txt` shows the child error arises inside `qcfractalcompute`/Parsl, not inside Psi4:
  - `qcfractalcompute/compute_manager.py`, `_acquire_complete_tasks`
  - `qcfractalcompute/apps/qcengine.py`, `qcengine_conda_app`
  - Python `tempfile.NamedTemporaryFile` cleanup
  - `FileNotFoundError: [Errno 2] No such file or directory: '/tmp/tmp4w28wzfc'`
- Failed children have no Psi4 stdout/stderr payload.
- Sibling children in the same manybody records often completed normally and show clean Psi4 termination:
  - `Psi4 exiting successfully`
  - normal `Psi4 wall time for execution` lines

## Interpretation

This does not look like bad geometries, wrong charge/multiplicity, bad basis names, or Psi4 convergence/runtime exceptions. Those would normally produce Psi4 stdout/stderr and a QCElemental/QCEngine/Psi4 error message.

Instead, the manager lost or could not clean up a temporary task-result file under `/tmp`. On Phoenix `free`, this is plausibly caused by jobs being killed/preempted or scratch/temp directories disappearing when the scheduler interrupts the job.

## Suggested Next Step

Resubmit only the 905 failed manybody rows to the same `free` tag or to a more stable queue if available. Since 1720 completed successfully with the same inputs and LoTs, the failed subset is safe to treat as retryable infrastructure failures.
