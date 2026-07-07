## Contents

- `plot_system_ordering.py`: plotting script.
- `system_ordering_value_slope_plot.png`: generated PNG figure.
- `system_ordering_value_slope_plot.pdf`: generated PDF figure.
- `environment.yml`: conda environment used to generate the figure.
- `<system>/`: per-system CSV inputs required by the script.

## Reproduce

```bash
conda env create -f environment.yml
conda activate qcml
python plot_system_ordering.py
```
