# Full Agentic Workflow Report

Budget: 9000 seconds (2.5 hours) for prediction filtering.
QCFractal: reachable at http://localhost:7777; completed duplicate records reused.
Manybody verification: 41 complete, 0 errored, 1 skipped missing complete duplicate.

## Predicted Accuracy Buckets
| Level of Theory          |   high_accuracy |   medium_accuracy |   low_accuracy |   not_recommended |   median_predicted_abs_percent_error |
|:-------------------------|----------------:|------------------:|---------------:|------------------:|-------------------------------------:|
| wB97X-V/aug-cc-pVTZ/CP   |               4 |                 1 |              1 |                 0 |                              1.77183 |
| B3LYP-D3/aug-cc-pVTZ/CP  |               1 |                 3 |              0 |                 2 |                              3.64094 |
| wB97X-D/aug-cc-pVTZ/CP   |               1 |                 2 |              2 |                 1 |                              5.06272 |
| B2PLYP-D3/aug-cc-pVTZ/CP |               0 |                 3 |              3 |                 0 |                              5.20062 |
| PBE-D3/aug-cc-pVTZ/CP    |               0 |                 0 |              1 |                 5 |                             15.2836  |
| MP2/aug-cc-pVTZ/CP       |               1 |                 0 |              0 |                 5 |                             37.1948  |
| HF/aug-cc-pVTZ/CP        |               0 |                 0 |              0 |                 6 |                            157.934   |

## Actual Error Summary By LoT
| Level of Theory          |   completed_rows |   mean_signed_error |   median_signed_error |   mean_abs_error |   median_actual_abs_percent_error |   median_walltime_hours |
|:-------------------------|-----------------:|--------------------:|----------------------:|-----------------:|----------------------------------:|------------------------:|
| B3LYP-D3/aug-cc-pVTZ/CP  |                6 |           -0.370006 |             0.0802821 |         0.987845 |                           2.54006 |                 5.06509 |
| B2PLYP-D3/aug-cc-pVTZ/CP |                5 |           -0.869815 |            -0.824388  |         0.869815 |                           4.74665 |                 6.90668 |
| wB97X-V/aug-cc-pVTZ/CP   |                6 |           -1.26995  |            -1.17441   |         1.26995  |                           5.48173 |                11.8105  |
| wB97X-D/aug-cc-pVTZ/CP   |                6 |           -2.60867  |            -2.75723   |         2.60867  |                          13.5909  |                10.3289  |
| PBE-D3/aug-cc-pVTZ/CP    |                6 |            1.92518  |             2.8064    |         3.1228   |                          14.6386  |                 3.63269 |
| MP2/aug-cc-pVTZ/CP       |                6 |          -11.4908   |           -13.317     |        11.4908   |                          52.9125  |                 6.33109 |
| HF/aug-cc-pVTZ/CP        |                6 |           33.222    |            36.4611    |        33.222    |                         161.349   |                 3.80446 |

## Recommended Completed Rows
| id     | Level of Theory          | accuracy_bucket   |   predicted_abs_percent_error |   actual_abs_percent_error |   IE_error_kcalmol |   walltime_hours |
|:-------|:-------------------------|:------------------|------------------------------:|---------------------------:|-------------------:|-----------------:|
| S8-2   | wB97X-D/aug-cc-pVTZ/CP   | high_accuracy     |                      0.143008 |                   1.97013  |         -0.606602  |         10.3192  |
| CBH    | MP2/aug-cc-pVTZ/CP       | high_accuracy     |                      0.754709 |                   4.88073  |         -0.539808  |          3.39115 |
| S8-2   | B3LYP-D3/aug-cc-pVTZ/CP  | high_accuracy     |                      0.940139 |                   0.236368 |         -0.0727777 |          5.43444 |
| C3A    | wB97X-V/aug-cc-pVTZ/CP   | high_accuracy     |                      1.165    |                   3.90594  |         -0.638231  |         15.4976  |
| CBH    | wB97X-V/aug-cc-pVTZ/CP   | high_accuracy     |                      1.2055   |                   9.81363  |         -1.08539   |         10.5241  |
| Da2    | wB97X-V/aug-cc-pVTZ/CP   | high_accuracy     |                      1.75233  |                   6.86009  |         -1.38574   |         11.2055  |
| S8-2   | wB97X-V/aug-cc-pVTZ/CP   | high_accuracy     |                      1.79133  |                   4.10336  |         -1.26342   |         12.4156  |
| C3A    | B3LYP-D3/aug-cc-pVTZ/CP  | medium_accuracy   |                      2.28535  |                   1.42804  |          0.233342  |          5.97071 |
| C3A    | B2PLYP-D3/aug-cc-pVTZ/CP | medium_accuracy   |                      2.90279  |                   5.04521  |         -0.824388  |          8.27032 |
| C2C2PD | wB97X-V/aug-cc-pVTZ/CP   | medium_accuracy   |                      3.2135   |                   2.64549  |         -0.546293  |          8.08851 |
| 2a     | B3LYP-D3/aug-cc-pVTZ/CP  | medium_accuracy   |                      3.56616  |                   2.97286  |         -1.01523   |          9.99058 |
| 2a     | wB97X-D/aug-cc-pVTZ/CP   | medium_accuracy   |                      3.68212  |                  14.1153   |         -4.82036   |         13.295   |
| Da2    | B3LYP-D3/aug-cc-pVTZ/CP  | medium_accuracy   |                      3.71572  |                   2.10726  |          0.425667  |          4.69574 |
| 2a     | B2PLYP-D3/aug-cc-pVTZ/CP | medium_accuracy   |                      3.84956  |                   4.87779  |         -1.66577   |          8.3508  |
| C2C2PD | wB97X-D/aug-cc-pVTZ/CP   | medium_accuracy   |                      4.36195  |                  13.0665   |         -2.69823   |          8.85559 |
| S8-2   | B2PLYP-D3/aug-cc-pVTZ/CP | medium_accuracy   |                      4.62871  |                   2.46294  |         -0.758338  |          6.90668 |
| 2a     | wB97X-V/aug-cc-pVTZ/CP   | low_accuracy      |                      5.34842  |                   7.90819  |         -2.70065   |         15.0148  |
| C3A    | wB97X-D/aug-cc-pVTZ/CP   | low_accuracy      |                      5.76349  |                  10.0474   |         -1.64174   |         13.2019  |
| Da2    | B2PLYP-D3/aug-cc-pVTZ/CP | low_accuracy      |                      5.77253  |                   4.74665  |         -0.958824  |          5.41458 |
| CBH    | B2PLYP-D3/aug-cc-pVTZ/CP | low_accuracy      |                      6.05704  |                   1.28171  |         -0.141757  |          4.74556 |
| Da2    | wB97X-D/aug-cc-pVTZ/CP   | low_accuracy      |                      8.38911  |                  15.1923   |         -3.06884   |         10.3386  |
| Da2    | PBE-D3/aug-cc-pVTZ/CP    | low_accuracy      |                      8.62047  |                  13.9067   |          2.80915   |          3.43799 |

## Overall Completed Error Stats
|        |   IE_error_kcalmol |
|:-------|-------------------:|
| mean   |           2.73407  |
| median |          -0.758338 |
| max    |          44.5089   |
| min    |         -16.8603   |

## Skipped/Missing Rows
| id     | Level of Theory          | job status                 |
|:-------|:-------------------------|:---------------------------|
| C2C2PD | B2PLYP-D3/aug-cc-pVTZ/CP | missing_complete_duplicate |
