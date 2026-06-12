# full-agentic-workflow Initial Report

Recommended LoT: B3LYP-D3/aug-cc-pVTZ/CP
Walltime budget: 9000 s (2.5 h)
Total candidate computations: 42
Budget-feasible computations submitted: 33
QCFractal status: initialized and reachable at http://localhost:7777

## Recommendation Summary
| Level of Theory         |   wins |   median_abs_error |   median_walltime_seconds |
|:------------------------|-------:|-------------------:|--------------------------:|
| B3LYP-D3/aug-cc-pVTZ/CP |      6 |           0.922419 |                   5332.56 |

## Per-System Winning LoT
| id     | Level of Theory         |   ERROR ESTIMATES (kcal/mol) |   walltime_seconds |
|:-------|:------------------------|-----------------------------:|-------------------:|
| 2a     | B3LYP-D3/aug-cc-pVTZ/CP |                   -2.21644   |            6367.11 |
| C2C2PD | B3LYP-D3/aug-cc-pVTZ/CP |                   -0.128919  |            2547.59 |
| C3A    | B3LYP-D3/aug-cc-pVTZ/CP |                    0.0862826 |            7119.39 |
| CBH    | B3LYP-D3/aug-cc-pVTZ/CP |                   -4.18396   |            5490.8  |
| Da2    | B3LYP-D3/aug-cc-pVTZ/CP |                   -1.71592   |            3954.03 |
| S8-2   | B3LYP-D3/aug-cc-pVTZ/CP |                    0.122659  |            5174.32 |

## Submitted Counts By LoT
| Level of Theory          |   submitted |   total_candidates |
|:-------------------------|------------:|-------------------:|
| B2PLYP-D3/aug-cc-pVTZ/CP |           5 |                  6 |
| B3LYP-D3/aug-cc-pVTZ/CP  |           6 |                  6 |
| HF/aug-cc-pVTZ/CP        |           6 |                  6 |
| MP2/aug-cc-pVTZ/CP       |           5 |                  6 |
| PBE-D3/aug-cc-pVTZ/CP    |           6 |                  6 |
| wB97X-D/aug-cc-pVTZ/CP   |           4 |                  6 |
| wB97X-V/aug-cc-pVTZ/CP   |           1 |                  6 |

## Above-Budget Rows Not Submitted
| id   | Level of Theory          |   walltime_seconds |   ERROR ESTIMATES (kcal/mol) |
|:-----|:-------------------------|-------------------:|-----------------------------:|
| C3A  | B2PLYP-D3/aug-cc-pVTZ/CP |           10128.3  |                    -1.59894  |
| C3A  | MP2/aug-cc-pVTZ/CP       |            9483.08 |                    -1.84649  |
| 2a   | wB97X-D/aug-cc-pVTZ/CP   |           10975    |                    -3.04524  |
| C3A  | wB97X-D/aug-cc-pVTZ/CP   |           12889.2  |                    -0.260998 |
| 2a   | wB97X-V/aug-cc-pVTZ/CP   |           15749.9  |                     0.18686  |
| C3A  | wB97X-V/aug-cc-pVTZ/CP   |           17874.7  |                    -0.979457 |
| CBH  | wB97X-V/aug-cc-pVTZ/CP   |           12975.9  |                     1.1472   |
| Da2  | wB97X-V/aug-cc-pVTZ/CP   |            9791.04 |                    -0.614568 |
| S8-2 | wB97X-V/aug-cc-pVTZ/CP   |           12799.4  |                    -1.58336  |

## Queued Records
| id     | Level of Theory          | qcfractal id   |   walltime_seconds |
|:-------|:-------------------------|:---------------|-------------------:|
| C3A    | HF/aug-cc-pVTZ/CP        | [1]            |            4216.65 |
| C2C2PD | HF/aug-cc-pVTZ/CP        | [2]            |            1284.4  |
| 2a     | HF/aug-cc-pVTZ/CP        | [3]            |            3480.21 |
| CBH    | HF/aug-cc-pVTZ/CP        | [4]            |            2212.08 |
| Da2    | HF/aug-cc-pVTZ/CP        | [5]            |            1924.49 |
| S8-2   | HF/aug-cc-pVTZ/CP        | [6]            |            2812.36 |
| C3A    | PBE-D3/aug-cc-pVTZ/CP    | [7]            |            3803.91 |
| C2C2PD | PBE-D3/aug-cc-pVTZ/CP    | [8]            |            1603.09 |
| 2a     | PBE-D3/aug-cc-pVTZ/CP    | [9]            |            3425.08 |
| CBH    | PBE-D3/aug-cc-pVTZ/CP    | [10]           |            2876.21 |
| Da2    | PBE-D3/aug-cc-pVTZ/CP    | [11]           |            2272.43 |
| S8-2   | PBE-D3/aug-cc-pVTZ/CP    | [12]           |            2860.18 |
| C2C2PD | wB97X-D/aug-cc-pVTZ/CP   | [13]           |            4290.44 |
| CBH    | wB97X-D/aug-cc-pVTZ/CP   | [14]           |            7775.66 |
| Da2    | wB97X-D/aug-cc-pVTZ/CP   | [15]           |            6396.01 |
| S8-2   | wB97X-D/aug-cc-pVTZ/CP   | [16]           |            8872.28 |
| C2C2PD | wB97X-V/aug-cc-pVTZ/CP   | [17]           |            6499.27 |
| C2C2PD | MP2/aug-cc-pVTZ/CP       | [18]           |            2647.24 |
| 2a     | MP2/aug-cc-pVTZ/CP       | [19]           |            7679.27 |
| CBH    | MP2/aug-cc-pVTZ/CP       | [20]           |            4661.38 |
| Da2    | MP2/aug-cc-pVTZ/CP       | [21]           |            4070.94 |
| S8-2   | MP2/aug-cc-pVTZ/CP       | [22]           |            6107.88 |
| C3A    | B3LYP-D3/aug-cc-pVTZ/CP  | [23]           |            7119.39 |
| C2C2PD | B3LYP-D3/aug-cc-pVTZ/CP  | [24]           |            2547.59 |
| 2a     | B3LYP-D3/aug-cc-pVTZ/CP  | [25]           |            6367.11 |
| CBH    | B3LYP-D3/aug-cc-pVTZ/CP  | [26]           |            5490.8  |
| Da2    | B3LYP-D3/aug-cc-pVTZ/CP  | [27]           |            3954.03 |
| S8-2   | B3LYP-D3/aug-cc-pVTZ/CP  | [28]           |            5174.32 |
| C2C2PD | B2PLYP-D3/aug-cc-pVTZ/CP | [29]           |            2939.95 |
| 2a     | B2PLYP-D3/aug-cc-pVTZ/CP | [30]           |            8264.59 |
| CBH    | B2PLYP-D3/aug-cc-pVTZ/CP | [31]           |            5238.84 |
| Da2    | B2PLYP-D3/aug-cc-pVTZ/CP | [32]           |            4491.91 |
| S8-2   | B2PLYP-D3/aug-cc-pVTZ/CP | [33]           |            6598.07 |

State files saved in this directory: select_lot_df.pkl, run_ies_input.pkl, geom_index.csv, reference_ie.csv, run_ies_queued.pkl.
