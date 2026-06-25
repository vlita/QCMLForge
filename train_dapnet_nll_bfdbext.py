import argparse
import shlex
import subprocess
from pathlib import Path


DEFAULT_METHODS = [
    "HF/aug-cc-pVTZ/CP",
    "PBE/aug-cc-pVTZ/CP",
    "wB97X-V/aug-cc-pVTZ/CP",
    "wB97X-D/aug-cc-pVTZ/CP",
    "MP2/aug-cc-pVTZ/CP",
    "B3LYP-D3/aug-cc-pVTZ/CP",
    "B2PLYP-D3/aug-cc-pVTZ/CP",
]
REFERENCE_METHOD = "CCSD(T)/CBS/CP"


def clean_str_for_filename(string):
    """Match dAPNet method-name cleanup used for checkpoint filenames."""
    string = string.replace("(", "_LP_").replace(")", "_RP_")
    string = "".join(e for e in string if e.isalnum() or e.isspace() or e in ["-", "_"])
    return string.replace(" ", "_")


def build_command(args, m1):
    m2 = args.reference_method
    m1_clean = clean_str_for_filename(m1)
    m2_clean = clean_str_for_filename(m2)
    model_out = Path(args.output_dir) / f"{m1_clean}_{m2_clean}.pt"
    am_model = args.am_model_path or str(Path(args.ap2_dir) / "am_0.pt")
    ap2_model = args.ap_pretrained_model_path or str(Path(args.ap2_dir) / "ap2_0.pt")

    return [
        args.python,
        "-u",
        args.train_script,
        "--train_apnet",
        "dAPNet2",
        "--am_model_path",
        am_model,
        "--ap_pretrained_model_path",
        ap2_model,
        "--ap_model_path",
        str(model_out),
        "--m1",
        m1,
        "--m2",
        m2,
        "--data_dir",
        args.data_dir,
        "--spec_type_ap",
        str(args.spec_type_ap),
        "--n_epochs",
        str(args.n_epochs),
        "--r_cut_im",
        str(args.r_cut_im),
        "--loss_type",
        "gaussian_nll",
        "--min_var",
        str(args.min_var),
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Generate or run BFDBExt dAPNet2 Gaussian NLL training commands."
    )
    parser.add_argument("--m1_list", nargs="+", default=DEFAULT_METHODS)
    parser.add_argument("--reference_method", default=REFERENCE_METHOD)
    parser.add_argument("--ap2_dir", default="./ap2")
    parser.add_argument(
        "--am_model_path",
        default=None,
        help="Atom model checkpoint. Defaults to <ap2_dir>/am_0.pt.",
    )
    parser.add_argument(
        "--ap_pretrained_model_path",
        default=None,
        help="AP2 backbone checkpoint. Defaults to <ap2_dir>/ap2_0.pt.",
    )
    parser.add_argument("--output_dir", default="./dap2_nll")
    parser.add_argument("--data_dir", default="./data_dir")
    parser.add_argument("--train_script", default="train_models.py")
    parser.add_argument("--python", default="python3")
    parser.add_argument("--spec_type_ap", type=int, default=1)
    parser.add_argument("--n_epochs", type=int, default=100)
    parser.add_argument("--r_cut_im", type=float, default=16.0)
    parser.add_argument("--min_var", type=float, default=1e-6)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run commands instead of printing them. Defaults to dry-run printing.",
    )
    args = parser.parse_args()

    for m1 in args.m1_list:
        command = build_command(args, m1)
        print(" ".join(shlex.quote(part) for part in command))
        if args.execute:
            Path(args.output_dir).mkdir(parents=True, exist_ok=True)
            subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
