from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

from apnet_pt.AtomPairwiseModels.dapnet2 import dAPNet2Model
from apnet_pt.pretrained_models import _resolve_dapnet2_pretrained_path


RUN_DIR = Path(__file__).resolve().parent
FEATURES_PATH = RUN_DIR / "HB375_BFDBExt_train_apnet2_pair_features.npz"
UMAP_CSV_PATH = RUN_DIR / "HB375_BFDBExt_train_apnet2_pair_umap.csv"
HB375_COMPARISON_PATH = RUN_DIR / "HB375_dapnet2_row_inference_comparison.pkl"
OUT_DIR = RUN_DIR / "contribution_tagged_umaps"
CONTRIB_CSV_PATH = OUT_DIR / "HB375_BFDBExt_train_pair_contributions_HF_wB97XV.csv"
HB375_SYSTEM_SUMMARY_PATH = OUT_DIR / "HB375_system_pair_contribution_summary_HF_wB97XV.csv"
DISTANCE_BIN_SUMMARY_PATH = OUT_DIR / "pair_contribution_distance_bins_HF_wB97XV.csv"
SUMMARY_PATH = OUT_DIR / "contribution_tagged_umap_summary.json"


METHODS = {
    "HF": "HF/aug-cc-pVTZ/CP",
    "wB97X-V": "wB97X-V/aug-cc-pVTZ/CP",
}


def contribution_columns(method_label: str) -> tuple[str, str]:
    safe = method_label.replace("-", "").replace("/", "_").replace(" ", "_")
    return f"{safe}_raw_pair_delta", f"{safe}_pred_ie_error_pair_contrib"


def compute_pair_contributions(features: np.ndarray, lot: str, batch_size: int = 65536) -> np.ndarray:
    model_path = _resolve_dapnet2_pretrained_path(lot, "CCSD(T)/CBS/CP")
    model = dAPNet2Model(pre_trained_model_path=model_path, use_GPU=False)
    model.model.eval()
    contributions = np.empty((len(features),), dtype=np.float32)
    for start in range(0, len(features), batch_size):
        stop = min(start + batch_size, len(features))
        batch = features[start:stop]
        h_ab = torch.tensor(batch[:, :122], dtype=torch.float32)
        h_ba = torch.tensor(batch[:, 122:244], dtype=torch.float32)
        cutoff = torch.tensor(batch[:, 244:], dtype=torch.float32)
        with torch.no_grad():
            eab = model.model.readout_layer_energy(h_ab)
            eba = model.model.readout_layer_energy(h_ba)
            raw_delta = ((eab + eba) * cutoff).flatten().cpu().numpy()
        contributions[start:stop] = raw_delta
    return contributions


def build_contribution_dataframe(force: bool = False) -> pd.DataFrame:
    if CONTRIB_CSV_PATH.exists() and not force:
        return pd.read_csv(CONTRIB_CSV_PATH, low_memory=False)

    OUT_DIR.mkdir(exist_ok=True)
    features = np.load(FEATURES_PATH)["features"]
    df = pd.read_csv(UMAP_CSV_PATH, low_memory=False)
    if len(df) != len(features):
        raise RuntimeError(f"Feature/UMAP row mismatch: {len(features)} vs {len(df)}")
    for method_label, lot in METHODS.items():
        raw_col, pred_col = contribution_columns(method_label)
        print(f"Computing pair contributions for {lot}", flush=True)
        raw = compute_pair_contributions(features, lot)
        df[raw_col] = raw
        # Workflow convention: the model's raw IE-error prediction is sign-flipped in post-processing.
        df[pred_col] = -raw
    df.to_csv(CONTRIB_CSV_PATH, index=False)
    return df


def symmetric_limits(values: pd.Series, quantile: float = 0.995) -> tuple[float, float]:
    vmax = float(values.abs().quantile(quantile))
    if vmax == 0 or np.isnan(vmax):
        vmax = float(values.abs().max())
    return -vmax, vmax


def plot_umap_contributions(df: pd.DataFrame) -> list[str]:
    paths = []
    x_margin = 0.05 * (df["umap_1"].max() - df["umap_1"].min())
    y_margin = 0.05 * (df["umap_2"].max() - df["umap_2"].min())
    xlim = (df["umap_1"].min() - x_margin, df["umap_1"].max() + x_margin)
    ylim = (df["umap_2"].min() - y_margin, df["umap_2"].max() + y_margin)

    for method_label in METHODS:
        _, pred_col = contribution_columns(method_label)
        for dataset_mode in ["all", "HB375"]:
            fig, ax = plt.subplots(figsize=(8, 7))
            if dataset_mode == "HB375":
                bg = df[df["dataset"] == "BFDBExt train"]
                ax.scatter(
                    bg["umap_1"], bg["umap_2"], color="lightgray", alpha=0.08,
                    s=3, linewidths=0, rasterized=True, label="BFDBExt train"
                )
                plot_df = df[df["dataset"] == "HB375"]
            else:
                plot_df = df
            vmin, vmax = symmetric_limits(plot_df[pred_col])
            sc = ax.scatter(
                plot_df["umap_1"],
                plot_df["umap_2"],
                c=plot_df[pred_col],
                cmap="coolwarm",
                vmin=vmin,
                vmax=vmax,
                alpha=0.75 if dataset_mode == "HB375" else 0.35,
                s=9 if dataset_mode == "HB375" else 4,
                linewidths=0,
                rasterized=True,
            )
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
            ax.set_xlabel("UMAP 1")
            ax.set_ylabel("UMAP 2")
            ax.set_title(f"{method_label} pair contribution to predicted IE error ({dataset_mode})")
            cbar = fig.colorbar(sc, ax=ax)
            cbar.set_label("Pair contribution (kcal/mol)")
            fig.tight_layout()
            path = OUT_DIR / f"umap_pair_contrib_{method_label.replace('-', '')}_{dataset_mode}.png"
            fig.savefig(path, dpi=300, bbox_inches="tight")
            plt.close(fig)
            paths.append(str(path))
    return paths


def plot_distance_dependence(df: pd.DataFrame) -> tuple[list[str], pd.DataFrame]:
    paths = []
    bin_rows = []
    for method_label in METHODS:
        _, pred_col = contribution_columns(method_label)
        fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
        for ax, dataset in zip(axes, ["BFDBExt train", "HB375"]):
            sub = df[df["dataset"] == dataset].copy()
            ax.scatter(
                sub["distance_angstrom"],
                sub[pred_col],
                alpha=0.08 if dataset == "BFDBExt train" else 0.18,
                s=4,
                linewidths=0,
                rasterized=True,
                color="#4c78a8" if dataset == "BFDBExt train" else "#e45756",
            )
            sub["distance_bin"] = pd.cut(sub["distance_angstrom"], bins=np.arange(0, 8.5, 0.5))
            grouped = sub.groupby("distance_bin", observed=True)[pred_col]
            centers = np.array([interval.mid for interval in grouped.mean().index])
            means = grouped.mean().to_numpy()
            abs_means = grouped.apply(lambda s: s.abs().mean()).to_numpy()
            counts = grouped.size().to_numpy()
            ax.plot(centers, means, color="black", linewidth=2, label="mean signed")
            ax.plot(centers, abs_means, color="goldenrod", linewidth=2, label="mean abs")
            ax.axhline(0, color="gray", linewidth=1)
            ax.set_title(dataset)
            ax.set_xlabel("Atom-pair distance (Angstrom)")
            ax.grid(alpha=0.2)
            for interval, mean, abs_mean, count in zip(grouped.mean().index, means, abs_means, counts):
                bin_rows.append(
                    {
                        "method": method_label,
                        "dataset": dataset,
                        "distance_bin": str(interval),
                        "distance_midpoint": float(interval.mid),
                        "mean_signed_pair_contribution": float(mean),
                        "mean_abs_pair_contribution": float(abs_mean),
                        "count": int(count),
                    }
                )
        axes[0].set_ylabel("Pair contribution to predicted IE error (kcal/mol)")
        axes[1].legend(frameon=False, loc="best")
        fig.suptitle(f"{method_label} pair contribution vs distance")
        fig.tight_layout()
        path = OUT_DIR / f"distance_pair_contrib_{method_label.replace('-', '')}.png"
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        paths.append(str(path))
    bins_df = pd.DataFrame(bin_rows)
    bins_df.to_csv(DISTANCE_BIN_SUMMARY_PATH, index=False)
    return paths, bins_df


def build_hb375_system_summary(df: pd.DataFrame) -> pd.DataFrame:
    hb_comp = pd.read_pickle(HB375_COMPARISON_PATH)
    hb_meta = hb_comp.drop_duplicates("id")[["id", "n_atoms", "benchmark_Eint"]].rename(columns={"id": "system_label"})
    rows = []
    hb_pairs = df[df["dataset"] == "HB375"]
    for system_label, sub in hb_pairs.groupby("system_label"):
        row = {"system_label": system_label, "pair_count": int(len(sub))}
        for method_label, lot in METHODS.items():
            raw_col, pred_col = contribution_columns(method_label)
            row[f"{method_label}_raw_sum_pair_delta"] = float(sub[raw_col].sum())
            row[f"{method_label}_pred_ie_error_from_pairs"] = float(sub[pred_col].sum())
            row[f"{method_label}_sum_abs_pair_contrib"] = float(sub[pred_col].abs().sum())
            row[f"{method_label}_mean_abs_pair_contrib"] = float(sub[pred_col].abs().mean())
            actual = hb_comp[(hb_comp["id"] == system_label) & (hb_comp["Level of Theory"] == lot)]
            if not actual.empty:
                row[f"{method_label}_stored_pred_ie_error"] = float(actual["PREDICTED IE Error"].iloc[0])
                row[f"{method_label}_actual_ie_error"] = float(actual["ACTUAL IE Error"].iloc[0])
                row[f"{method_label}_prediction_residual"] = float(actual["PREDICTED_minus_ACTUAL_IE_Error"].iloc[0])
        rows.append(row)
    summary = pd.DataFrame(rows).merge(hb_meta, on="system_label", how="left")
    summary.to_csv(HB375_SYSTEM_SUMMARY_PATH, index=False)
    return summary


def plot_system_scaling(summary: pd.DataFrame) -> list[str]:
    paths = []
    for method_label in METHODS:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        axes[0].scatter(
            summary["n_atoms"],
            summary[f"{method_label}_sum_abs_pair_contrib"],
            c=summary[f"{method_label}_prediction_residual"].abs(),
            cmap="magma",
            s=35,
            alpha=0.8,
        )
        axes[0].set_xlabel("HB375 atoms")
        axes[0].set_ylabel("Sum |pair contribution| (kcal/mol)")
        axes[0].set_title("Magnitude vs system size")
        axes[0].grid(alpha=0.2)

        sc = axes[1].scatter(
            summary["pair_count"],
            summary[f"{method_label}_prediction_residual"],
            c=summary[f"{method_label}_sum_abs_pair_contrib"],
            cmap="viridis",
            s=35,
            alpha=0.8,
        )
        axes[1].axhline(0, color="gray", linewidth=1)
        axes[1].set_xlabel("HB375 APNet2 atom-pair count")
        axes[1].set_ylabel("Predicted - actual IE error (kcal/mol)")
        axes[1].set_title("Residual vs pair count")
        axes[1].grid(alpha=0.2)
        cbar = fig.colorbar(sc, ax=axes[1])
        cbar.set_label("Sum |pair contribution| (kcal/mol)")
        fig.suptitle(f"{method_label} HB375 contribution scaling")
        fig.tight_layout()
        path = OUT_DIR / f"HB375_system_scaling_{method_label.replace('-', '')}.png"
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        paths.append(str(path))
    return paths


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    df = build_contribution_dataframe()
    umap_paths = plot_umap_contributions(df)
    distance_paths, bins_df = plot_distance_dependence(df)
    system_summary = build_hb375_system_summary(df)
    scaling_paths = plot_system_scaling(system_summary)

    checks = {}
    for method_label in METHODS:
        checks[method_label] = {
            "max_abs_pair_sum_minus_stored_pred": float(
                (system_summary[f"{method_label}_pred_ie_error_from_pairs"] - system_summary[f"{method_label}_stored_pred_ie_error"]).abs().max()
            ),
            "corr_sum_abs_pair_contrib_vs_n_atoms": float(
                system_summary[["n_atoms", f"{method_label}_sum_abs_pair_contrib"]].corr().iloc[0, 1]
            ),
            "corr_abs_residual_vs_pair_count": float(
                np.corrcoef(
                    system_summary["pair_count"],
                    system_summary[f"{method_label}_prediction_residual"].abs(),
                )[0, 1]
            ),
            "mean_abs_pair_contribution_HB375": float(
                df.loc[df["dataset"] == "HB375", contribution_columns(method_label)[1]].abs().mean()
            ),
            "mean_abs_pair_contribution_BFDBExt_train": float(
                df.loc[df["dataset"] == "BFDBExt train", contribution_columns(method_label)[1]].abs().mean()
            ),
        }

    summary = {
        "contribution_csv": str(CONTRIB_CSV_PATH),
        "hb375_system_summary_csv": str(HB375_SYSTEM_SUMMARY_PATH),
        "distance_bin_summary_csv": str(DISTANCE_BIN_SUMMARY_PATH),
        "umap_plots": umap_paths,
        "distance_plots": distance_paths,
        "system_scaling_plots": scaling_paths,
        "pair_rows": int(len(df)),
        "distance_bin_rows": int(len(bins_df)),
        "hb375_system_rows": int(len(system_summary)),
        "contribution_definition": "pred_ie_error_pair_contrib = -((readout(h_AB) + readout(h_BA)) * cutoff), matching workflow sign flip",
        "checks": checks,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
