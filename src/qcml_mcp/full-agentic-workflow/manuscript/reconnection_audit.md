# QCFractal Reconnection Audit

Expected queued records: 42
Unique expected QCFractal IDs: 42
Records found on server: 42
Missing records: 0
Status counts: {'running': 20, 'complete': 13, 'waiting': 9}
Child status counts: {'complete': 40, 'running': 3, 'waiting': 56}
Completed records missing IE property: 0

## Missing Records
None

## Completed Records
| id     | expected_lot           |   qcf_id | completed_ie_present   |
|:-------|:-----------------------|---------:|:-----------------------|
| C3A    | HF/aug-cc-pVTZ/CP      |        1 | True                   |
| C2C2PD | HF/aug-cc-pVTZ/CP      |        2 | True                   |
| 2a     | HF/aug-cc-pVTZ/CP      |        3 | True                   |
| CBH    | HF/aug-cc-pVTZ/CP      |        4 | True                   |
| Da2    | HF/aug-cc-pVTZ/CP      |        5 | True                   |
| S8-2   | HF/aug-cc-pVTZ/CP      |        6 | True                   |
| C3A    | PBE-D3/aug-cc-pVTZ/CP  |        7 | True                   |
| C2C2PD | PBE-D3/aug-cc-pVTZ/CP  |        8 | True                   |
| 2a     | PBE-D3/aug-cc-pVTZ/CP  |        9 | True                   |
| CBH    | PBE-D3/aug-cc-pVTZ/CP  |       10 | True                   |
| Da2    | PBE-D3/aug-cc-pVTZ/CP  |       11 | True                   |
| S8-2   | PBE-D3/aug-cc-pVTZ/CP  |       12 | True                   |
| C2C2PD | wB97X-D/aug-cc-pVTZ/CP |       13 | True                   |

## Noncomplete Records
| id     | expected_lot             |   qcf_id | status   | child_statuses                |
|:-------|:-------------------------|---------:|:---------|:------------------------------|
| CBH    | wB97X-D/aug-cc-pVTZ/CP   |       14 | running  | {'running': 1, 'waiting': 2}  |
| Da2    | wB97X-D/aug-cc-pVTZ/CP   |       15 | running  | {'complete': 1, 'running': 2} |
| S8-2   | wB97X-D/aug-cc-pVTZ/CP   |       16 | running  | {'waiting': 3}                |
| C2C2PD | wB97X-V/aug-cc-pVTZ/CP   |       17 | running  | {'waiting': 3}                |
| C2C2PD | MP2/aug-cc-pVTZ/CP       |       18 | running  | {'waiting': 3}                |
| 2a     | MP2/aug-cc-pVTZ/CP       |       19 | running  | {'waiting': 3}                |
| CBH    | MP2/aug-cc-pVTZ/CP       |       20 | running  | {'waiting': 3}                |
| Da2    | MP2/aug-cc-pVTZ/CP       |       21 | running  | {'waiting': 3}                |
| S8-2   | MP2/aug-cc-pVTZ/CP       |       22 | running  | {'waiting': 3}                |
| C3A    | B3LYP-D3/aug-cc-pVTZ/CP  |       23 | running  | {'waiting': 3}                |
| C2C2PD | B3LYP-D3/aug-cc-pVTZ/CP  |       24 | running  | {'waiting': 3}                |
| 2a     | B3LYP-D3/aug-cc-pVTZ/CP  |       25 | running  | {'waiting': 3}                |
| CBH    | B3LYP-D3/aug-cc-pVTZ/CP  |       26 | running  | {'waiting': 3}                |
| Da2    | B3LYP-D3/aug-cc-pVTZ/CP  |       27 | running  | {'waiting': 3}                |
| S8-2   | B3LYP-D3/aug-cc-pVTZ/CP  |       28 | running  | {'waiting': 3}                |
| C2C2PD | B2PLYP-D3/aug-cc-pVTZ/CP |       29 | running  | {'waiting': 3}                |
| 2a     | B2PLYP-D3/aug-cc-pVTZ/CP |       30 | running  | {'waiting': 3}                |
| CBH    | B2PLYP-D3/aug-cc-pVTZ/CP |       31 | running  | {'waiting': 3}                |
| Da2    | B2PLYP-D3/aug-cc-pVTZ/CP |       32 | running  | {'waiting': 3}                |
| S8-2   | B2PLYP-D3/aug-cc-pVTZ/CP |       33 | running  | {'waiting': 3}                |
| C3A    | wB97X-D/aug-cc-pVTZ/CP   |       94 | waiting  | {}                            |
| 2a     | wB97X-D/aug-cc-pVTZ/CP   |       95 | waiting  | {}                            |
| C3A    | wB97X-V/aug-cc-pVTZ/CP   |       96 | waiting  | {}                            |
| 2a     | wB97X-V/aug-cc-pVTZ/CP   |       97 | waiting  | {}                            |
| CBH    | wB97X-V/aug-cc-pVTZ/CP   |       98 | waiting  | {}                            |
| Da2    | wB97X-V/aug-cc-pVTZ/CP   |       99 | waiting  | {}                            |
| S8-2   | wB97X-V/aug-cc-pVTZ/CP   |      100 | waiting  | {}                            |
| C3A    | MP2/aug-cc-pVTZ/CP       |      101 | waiting  | {}                            |
| C3A    | B2PLYP-D3/aug-cc-pVTZ/CP |      102 | waiting  | {}                            |
