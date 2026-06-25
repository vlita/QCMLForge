import argparse
import csv
from pathlib import Path

import numpy as np
import torch
from torch_geometric.data import Data

from apnet_pt import util
from apnet_pt.AtomPairwiseModels.apnet2 import APNet2Model
from apnet_pt.AtomPairwiseModels.dapnet2 import dAPNet2Model, _dapnet_mu_var
from apnet_pt.pt_datasets.dapnet_ds import clean_str_for_filename


METHODS = [
    "HF/aug-cc-pVTZ/CP",
    "PBE/aug-cc-pVTZ/CP",
    "wB97X-V/aug-cc-pVTZ/CP",
    "wB97X-D/aug-cc-pVTZ/CP",
    "MP2/aug-cc-pVTZ/CP",
    "B3LYP-D3/aug-cc-pVTZ/CP",
    "B2PLYP-D3/aug-cc-pVTZ/CP",
]
REFERENCE = "CCSD(T)/CBS/CP"


def model_filename(m1, m2):
    return f"{clean_str_for_filename(m1)}_{clean_str_for_filename(m2)}.pt"


def load_split(raw_path, methods, reference):
    columns = list(methods) + [reference]
    qcel_mols, labels = util.load_dimer_dataset(
        raw_path,
        max_size=None,
        return_qcel_mols=True,
        return_qcel_mons=False,
        columns=columns,
    )
    ref = labels[:, -1]
    targets = {method: labels[:, i] - ref for i, method in enumerate(methods)}
    return qcel_mols, targets


def metrics(errors):
    errors = np.asarray(errors, dtype=float)
    return {
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "bias": float(np.mean(errors)),
        "max_abs": float(np.max(np.abs(errors))),
    }


def make_dapnet(checkpoint, ap2_model, device):
    model = dAPNet2Model(
        apnet2_model=ap2_model,
        pre_trained_model_path=str(checkpoint),
        ignore_database_null=True,
        use_GPU=device.type == "cuda",
    )
    model.model.to(device)
    model.model.eval()
    return model


def eval_model_on_hidden(model, hidden_batch):
    with torch.no_grad():
        outputs = model.eval_fn(hidden_batch)
    if getattr(model, "loss_type", "mse") == "gaussian_nll":
        mu, var = _dapnet_mu_var(outputs, min_var=getattr(model, "min_var", 1e-6))
        return mu.detach().cpu().numpy(), torch.sqrt(var).detach().cpu().numpy()
    return outputs.flatten().detach().cpu().numpy(), None


def empty_accum():
    accum = {}
    for method in METHODS:
        accum[(method, "mse")] = []
        accum[(method, "nll")] = []
        accum[(method, "nll_sigma")] = []
    return accum


def rows_from_accum(split_name, route, accum):
    rows = []
    for method in METHODS:
        mse = metrics(accum[(method, "mse")])
        nll = metrics(accum[(method, "nll")])
        sigma = np.asarray(accum[(method, "nll_sigma")], dtype=float)
        rows.append(
            {
                "split": split_name,
                "route": route,
                "method": method,
                "n": len(accum[(method, "mse")]),
                "mse_mae": mse["mae"],
                "nll_mae": nll["mae"],
                "delta_mae_nll_minus_mse": nll["mae"] - mse["mae"],
                "mse_rmse": mse["rmse"],
                "nll_rmse": nll["rmse"],
                "mse_bias": mse["bias"],
                "nll_bias": nll["bias"],
                "mse_max_abs": mse["max_abs"],
                "nll_max_abs": nll["max_abs"],
                "nll_sigma_mean": float(np.mean(sigma)),
                "nll_sigma_median": float(np.median(sigma)),
            }
        )
    return rows


def evaluate_split_hidden(split_name, raw_path, args, ap2_model, models, device):
    qcel_mols, targets = load_split(raw_path, METHODS, args.reference_method)
    accum = empty_accum()

    for start in range(0, len(qcel_mols), args.batch_size):
        stop = min(start + args.batch_size, len(qcel_mols))
        batch_mols = qcel_mols[start:stop]
        _, h_abs, h_bas, cutoffs, dimer_inds, ndimers = ap2_model.predict_qcel_mols(
            mols=batch_mols,
            batch_size=args.batch_size,
            r_cut=ap2_model.model.r_cut,
            r_cut_im=ap2_model.model.r_cut_im,
        )
        hidden_batch = Data(
            h_AB=h_abs[0].detach().clone(),
            h_BA=h_bas[0].detach().clone(),
            cutoff=cutoffs[0].detach().clone(),
            dimer_ind=dimer_inds[0].detach().clone(),
            ndimer=ndimers[0],
        ).to(device)

        for method in METHODS:
            target = targets[method][start:stop]
            pred, _ = eval_model_on_hidden(models[(method, "mse")], hidden_batch)
            # Previous workflow trained CCSD(T)->method and copied that model to
            # method->CCSD(T), so the MSE checkpoint predicts the correction to
            # add to the raw method-reference error.
            accum[(method, "mse")].extend(target + pred)

            pred, sigma = eval_model_on_hidden(models[(method, "nll")], hidden_batch)
            # NLL checkpoints here were trained directly on method-reference,
            # so subtract their predicted delta from the raw error.
            accum[(method, "nll")].extend(target - pred)
            accum[(method, "nll_sigma")].extend(sigma)

    return rows_from_accum(split_name, "hidden", accum)


def evaluate_split_public(split_name, raw_path, args, models):
    qcel_mols, targets = load_split(raw_path, METHODS, args.reference_method)
    accum = empty_accum()
    for method in METHODS:
        target = targets[method]
        mse_pred = models[(method, "mse")].predict_qcel_mols(
            qcel_mols,
            batch_size=args.batch_size,
        )
        nll_pred, nll_sigma = models[(method, "nll")].predict_qcel_mols(
            qcel_mols,
            batch_size=args.batch_size,
            return_uncertainty=True,
        )
        accum[(method, "mse")].extend(target + mse_pred)
        accum[(method, "nll")].extend(target - nll_pred)
        accum[(method, "nll_sigma")].extend(nll_sigma)
    return rows_from_accum(split_name, "public", accum)


def main():
    parser = argparse.ArgumentParser(description="Compare MSE and NLL dAPNet models.")
    parser.add_argument("--data_dir", required=True)
    parser.add_argument("--mse_dir", required=True)
    parser.add_argument("--nll_dir", required=True)
    parser.add_argument("--am_model_path", required=True)
    parser.add_argument("--ap_pretrained_model_path", required=True)
    parser.add_argument("--reference_method", default=REFERENCE)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--output_csv", default="dapnet_mse_vs_nll.csv")
    parser.add_argument(
        "--route",
        choices=["hidden", "public", "both"],
        default="both",
        help="Evaluation route: shared AP2 hidden states, public predict_qcel_mols, or both.",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["test"],
        choices=["train", "test"],
        help="BFDBExt splits to evaluate (default: test).",
    )
    parser.add_argument("--use_gpu", action="store_true")
    args = parser.parse_args()

    device = torch.device("cuda:0" if args.use_gpu and torch.cuda.is_available() else "cpu")

    ap2_model = APNet2Model(
        atom_model_pre_trained_path=args.am_model_path,
        pre_trained_model_path=args.ap_pretrained_model_path,
        ignore_database_null=True,
        use_GPU=args.use_gpu,
        r_cut_im=16.0,
    ).set_return_hidden_states(True)
    ap2_model.model.to(device)
    ap2_model.model.eval()

    models = {}
    for method in METHODS:
        name = model_filename(method, args.reference_method)
        models[(method, "mse")] = make_dapnet(Path(args.mse_dir) / name, ap2_model, device)
        models[(method, "nll")] = make_dapnet(Path(args.nll_dir) / name, ap2_model, device)

    rows = []
    for split in args.splits:
        raw_path = Path(args.data_dir) / "raw" / f"3324_BFDBext_{split}_dimers.pkl"
        if args.route in {"hidden", "both"}:
            rows.extend(evaluate_split_hidden(split, raw_path, args, ap2_model, models, device))
        if args.route in {"public", "both"}:
            rows.extend(evaluate_split_public(split, raw_path, args, models))

    with open(args.output_csv, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {args.output_csv}")
    for row in rows:
        print(
            f"{row['split']:>5} {row['method']:<28} "
            f"{row['route']:<6} "
            f"MSE MAE={row['mse_mae']:.6f} NLL MAE={row['nll_mae']:.6f} "
            f"delta={row['delta_mae_nll_minus_mse']:+.6f} "
            f"sigma_med={row['nll_sigma_median']:.6f}"
        )


if __name__ == "__main__":
    main()
