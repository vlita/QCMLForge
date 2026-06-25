from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler

import apnet_pt
from apnet_pt import AtomModels, AtomPairwiseModels
from qm_tools_aw.tools import convert_schr_row_to_mol


RUN_DIR = Path(__file__).resolve().parent
BFDBEXT_TRAIN_PATH = Path(
    "/projects/cos-lab-cs207/ds/vlita3/projects/gits/AI4Science_QC/"
    "qcml_models/data_dir/raw/3324_BFDBext_train_dimers.pkl"
)
HB375_PATH = RUN_DIR / "HB375_dapnet2_row_inference_comparison.pkl"

PAIR_FEATURES_PATH = RUN_DIR / "HB375_BFDBExt_train_apnet2_pair_features.npz"
ANNOTATIONS_PATH = RUN_DIR / "HB375_BFDBExt_train_apnet2_pair_annotations.csv"
UMAP_CSV_PATH = RUN_DIR / "HB375_BFDBExt_train_apnet2_pair_umap.csv"
UMAP_PNG_PATH = RUN_DIR / "HB375_BFDBExt_train_apnet2_pair_umap_by_dataset.png"
SUMMARY_PATH = RUN_DIR / "HB375_BFDBExt_train_apnet2_pair_umap_summary.json"


def atomic_symbol(atomic_number: int) -> str:
    periodic_table = {
        1: "H",
        6: "C",
        7: "N",
        8: "O",
        9: "F",
        15: "P",
        16: "S",
        17: "Cl",
        35: "Br",
        53: "I",
    }
    return periodic_table.get(int(atomic_number), f"Z{atomic_number}")


def estimate_hybridization(mol, atom_idx: int, bond_cutoff: float = 1.7) -> str:
    coords = mol.geometry.reshape(-1, 3) * apnet_pt.constants.au2ang
    atom_coord = coords[atom_idx]
    atomic_num = mol.atomic_numbers[atom_idx]
    distances = np.linalg.norm(coords - atom_coord, axis=1)
    n_neighbors = int(np.sum((distances > 0.01) & (distances < bond_cutoff)))
    if atomic_num in [6, 7, 8]:
        if n_neighbors <= 2:
            return "sp"
        if n_neighbors == 3:
            return "sp2"
        return "sp3"
    return f"n{n_neighbors}"


def load_systems() -> pd.DataFrame:
    bfdb = pd.read_pickle(BFDBEXT_TRAIN_PATH).copy()
    bfdb["dataset"] = "BFDBExt train"
    bfdb["source_row"] = np.arange(len(bfdb))
    bfdb["system_label"] = bfdb["id"].astype(str)
    bfdb["qcel_mol"] = bfdb.apply(lambda row: convert_schr_row_to_mol(row), axis=1)
    bfdb = bfdb[["dataset", "source_row", "system_label", "qcel_mol"]]

    hb = pd.read_pickle(HB375_PATH)
    hb = hb.drop_duplicates("id").copy()
    hb["dataset"] = "HB375"
    hb["source_row"] = np.arange(len(hb))
    hb["system_label"] = hb["id"].astype(str)
    hb["qcel_mol"] = hb["qcel_dimer"]
    hb = hb[["dataset", "source_row", "system_label", "qcel_mol"]]

    systems = pd.concat([bfdb, hb], ignore_index=True)
    bad = systems["qcel_mol"].map(lambda mol: len(getattr(mol, "fragments", [])) != 2)
    if bad.any():
        raise RuntimeError(f"Found {int(bad.sum())} systems without two fragments")
    return systems


def build_apnet2_model():
    atom_model = AtomModels.ap2_atom_model.AtomModel(
        ds_root=None,
        ignore_database_null=True,
        use_GPU=False,
    ).set_pretrained_model(model_id=0)
    apnet2 = AtomPairwiseModels.apnet2.APNet2Model(
        atom_model=atom_model.model,
        use_GPU=False,
    ).set_pretrained_model(model_id=0)
    apnet2.model.return_hidden_states = True
    return apnet2


def pair_annotations(mol, row, pair_count: int) -> list[dict[str, object]]:
    mon_a = mol.get_fragment(0)
    mon_b = mol.get_fragment(1)
    e_ab_source, e_ab_target, _, _ = apnet_pt.pairwise_datasets.pairwise_edges_im(
        torch.tensor(mon_a.geometry) * apnet_pt.constants.au2ang,
        torch.tensor(mon_b.geometry) * apnet_pt.constants.au2ang,
        r_cut_im=8.0,
    )
    dist = np.linalg.norm(
        mon_a.geometry.reshape(-1, 3)[:, np.newaxis, :] * apnet_pt.constants.au2ang
        - mon_b.geometry.reshape(-1, 3)[np.newaxis, :, :] * apnet_pt.constants.au2ang,
        axis=-1,
    )
    if len(e_ab_source) != pair_count:
        raise RuntimeError(
            f"Pair count mismatch for {row.system_label}: "
            f"edges={len(e_ab_source)}, embeddings={pair_count}"
        )

    annotations = []
    a_offset = 0
    b_offset = len(mon_a.atomic_numbers)
    for pair_idx in range(pair_count):
        atom_a_idx = int(e_ab_source[pair_idx].item())
        atom_b_idx = int(e_ab_target[pair_idx].item())
        global_a_idx = a_offset + atom_a_idx
        global_b_idx = b_offset + atom_b_idx
        elem_a = atomic_symbol(mon_a.atomic_numbers[atom_a_idx])
        elem_b = atomic_symbol(mon_b.atomic_numbers[atom_b_idx])
        hybrid_a = estimate_hybridization(mol, global_a_idx)
        hybrid_b = estimate_hybridization(mol, global_b_idx)
        pair_label = "-".join(sorted([elem_a, elem_b]))
        element_hybrid_pair = "-".join(
            sorted([f"{elem_a}_{hybrid_a}", f"{elem_b}_{hybrid_b}"])
        )
        annotations.append(
            {
                "dataset": row.dataset,
                "system_label": row.system_label,
                "source_row": int(row.source_row),
                "pair_in_system": pair_idx,
                "atom_A_idx": atom_a_idx,
                "atom_B_idx": atom_b_idx,
                "element_A": elem_a,
                "element_B": elem_b,
                "pair_label": pair_label,
                "distance_angstrom": float(dist[atom_a_idx, atom_b_idx]),
                "hybrid_A": hybrid_a,
                "hybrid_B": hybrid_b,
                "hybrid_pair": f"{hybrid_a}-{hybrid_b}",
                "element_hybrid_pair": element_hybrid_pair,
            }
        )
    return annotations


def extract_pair_features(force: bool = False) -> tuple[np.ndarray, pd.DataFrame]:
    if not force and PAIR_FEATURES_PATH.exists() and ANNOTATIONS_PATH.exists():
        features = np.load(PAIR_FEATURES_PATH)["features"]
        annotations = pd.read_csv(ANNOTATIONS_PATH)
        return features, annotations

    systems = load_systems()
    apnet2 = build_apnet2_model()
    features = []
    annotations = []
    for idx, row in systems.iterrows():
        mol = row.qcel_mol
        print(
            f"Extracting APNet2 pair embeddings {idx + 1}/{len(systems)}: "
            f"{row.dataset} {row.system_label}",
            flush=True,
        )
        with torch.no_grad():
            _, h_abs, h_bas, cutoffs, _, _ = apnet2.predict_qcel_mols(
                mols=[mol],
                batch_size=1,
                r_cut=apnet2.model.r_cut,
                r_cut_im=apnet2.model.r_cut_im,
            )
        h_ab = h_abs[0].detach().cpu().numpy()
        h_ba = h_bas[0].detach().cpu().numpy()
        cutoff = cutoffs[0].detach().cpu().numpy()
        system_features = np.concatenate([h_ab, h_ba, cutoff], axis=1)
        features.append(system_features)
        annotations.extend(pair_annotations(mol, row, len(system_features)))

    feature_array = np.vstack(features).astype(np.float32)
    annotations_df = pd.DataFrame(annotations)
    np.savez_compressed(PAIR_FEATURES_PATH, features=feature_array)
    annotations_df.to_csv(ANNOTATIONS_PATH, index=False)
    return feature_array, annotations_df


def run_umap(force_features: bool = False, force_umap: bool = False) -> pd.DataFrame:
    if not force_umap and UMAP_CSV_PATH.exists():
        return pd.read_csv(UMAP_CSV_PATH)

    features, annotations = extract_pair_features(force=force_features)
    import umap

    scaled = StandardScaler().fit_transform(features)
    reducer = umap.UMAP(
        n_neighbors=15,
        min_dist=0.1,
        n_components=2,
        metric="euclidean",
        random_state=42,
    )
    embedding = reducer.fit_transform(scaled)
    result = annotations.copy()
    result["umap_1"] = embedding[:, 0]
    result["umap_2"] = embedding[:, 1]
    result["reducer"] = "UMAP"
    result.to_csv(UMAP_CSV_PATH, index=False)
    return result


def plot_dataset_umap(result: pd.DataFrame) -> None:
    plt.figure(figsize=(9, 7))
    styles = {
        "BFDBExt train": {"color": "#4c78a8", "alpha": 0.12, "s": 4},
        "HB375": {"color": "#e45756", "alpha": 0.65, "s": 10},
    }
    for dataset, style in styles.items():
        sub = result[result["dataset"] == dataset]
        plt.scatter(
            sub["umap_1"],
            sub["umap_2"],
            label=f"{dataset} (n={len(sub):,} pairs)",
            linewidths=0,
            rasterized=True,
            **style,
        )
    reducer_name = result["reducer"].iloc[0] if "reducer" in result else "UMAP"
    plt.xlabel(f"{reducer_name} 1")
    plt.ylabel(f"{reducer_name} 2")
    plt.title("APNet2 Atom-Pair Featurization Space")
    plt.legend(frameon=False, loc="best")
    plt.tight_layout()
    plt.savefig(UMAP_PNG_PATH, dpi=300, bbox_inches="tight")
    plt.close()


def main() -> None:
    result = run_umap()
    plot_dataset_umap(result)
    summary = {
        "bfdbext_train_path": str(BFDBEXT_TRAIN_PATH),
        "hb375_path": str(HB375_PATH),
        "pair_features_path": str(PAIR_FEATURES_PATH),
        "annotations_path": str(ANNOTATIONS_PATH),
        "umap_csv_path": str(UMAP_CSV_PATH),
        "umap_png_path": str(UMAP_PNG_PATH),
        "rows": int(len(result)),
        "reducer": str(result["reducer"].iloc[0]) if "reducer" in result else "UMAP",
        "dataset_pair_counts": {
            k: int(v) for k, v in result["dataset"].value_counts().items()
        },
        "unique_system_counts": {
            k: int(v)
            for k, v in result.groupby("dataset")["system_label"].nunique().items()
        },
        "top_element_pairs": result["pair_label"].value_counts().head(20).to_dict(),
        "top_element_hybrid_pairs": result["element_hybrid_pair"]
        .value_counts()
        .head(20)
        .to_dict(),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
