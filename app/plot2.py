"""
Plot Pseudorange and carrier phase from RINEX observation file.
"""

from pathlib import Path
import argparse
import georinex as gr
import warnings
from logging import getLogger, basicConfig, INFO

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

logger = getLogger(__name__)
basicConfig(level=INFO, format="%(asctime)s %(levelname)s %(message)s")

CLIGHT = 299792458.0
L1_FREQ = 1.57542e9
L2_FREQ = 1.22760e9
L5_FREQ = 1.17645e9
wlen_L1 = CLIGHT / L1_FREQ
wlen_L2 = CLIGHT / L2_FREQ
wlen_L5 = CLIGHT / L5_FREQ
logger.info(f"wlen_L1: {wlen_L1}, wlen_L2: {wlen_L2}, wlen_L5: {wlen_L5}")

wl_wlen = CLIGHT / (L1_FREQ - L2_FREQ)
nl_wlen = CLIGHT / (L1_FREQ + L2_FREQ)
iono_wlen = (L1_FREQ**2) / (L1_FREQ**2 - L2_FREQ**2) * wlen_L1 + (L2_FREQ**2) / (
    L1_FREQ**2 - L2_FREQ**2
) * wlen_L2
logger.info(f"wl_wlen: {wl_wlen}, nl_wlen: {nl_wlen} iono_wlen: {iono_wlen}")


def get_wineline_ambiguity(rnxobs, satname: str):
    pr_l1 = rnxobs["C1C"].sel(sv=satname)
    cp_l1 = rnxobs["L1C"].sel(sv=satname)
    pr_l2 = rnxobs["C2X"].sel(sv=satname)
    cp_l2 = rnxobs["L2X"].sel(sv=satname)
    time = rnxobs.time
    # Wide-lane (phase): L1 - L2
    wl_cp = cp_l1 - cp_l2
    wl_wlen = CLIGHT / (L1_FREQ - L2_FREQ)
    # Narrow-lane (code): L1 + L2
    nl_pr = (
        L1_FREQ / (L1_FREQ + L2_FREQ) * pr_l1 + L2_FREQ / (L1_FREQ + L2_FREQ) * pr_l2
    )
    amb_wl = wl_cp - nl_pr / wl_wlen
    return time, amb_wl


def get_narrowline_ambiguity(rnxobs, satname: str, amb_wl_mean: float):
    pr_l1 = rnxobs["C1C"].sel(sv=satname)
    cp_l1 = rnxobs["L1C"].sel(sv=satname)
    pr_l2 = rnxobs["C2X"].sel(sv=satname)
    cp_l2 = rnxobs["L2X"].sel(sv=satname)
    time = rnxobs.time

    # Iono-free combination
    pr_if = (L1_FREQ**2 * pr_l1 - L2_FREQ**2 * pr_l2) / (L1_FREQ**2 - L2_FREQ**2)
    cp_if = (L1_FREQ**2 * wlen_L1 * cp_l1 - L2_FREQ**2 * wlen_L2 * cp_l2) / (
        L1_FREQ**2 - L2_FREQ**2
    )
    amb_n1 = (
        cp_if
        - pr_if
        - (-(L2_FREQ**2)) / (L1_FREQ**2 - L2_FREQ**2) * wlen_L2 * amb_wl_mean
    ) / (
        (L1_FREQ**2) / (L1_FREQ**2 - L2_FREQ**2) * wlen_L1
        + (L2_FREQ**2) / (L1_FREQ**2 - L2_FREQ**2) * wlen_L2
    )
    return time, amb_n1


def get_ionospheric_ambiguity(rnxobs, satname: str):
    pr_l1 = rnxobs["C1C"].sel(sv=satname)
    cp_l1 = rnxobs["L1C"].sel(sv=satname)
    pr_l2 = rnxobs["C2X"].sel(sv=satname)
    cp_l2 = rnxobs["L2X"].sel(sv=satname)
    time = rnxobs.time

    # Iono-free combination
    pr_if = (L1_FREQ**2 * pr_l1 - L2_FREQ**2 * pr_l2) / (L1_FREQ**2 - L2_FREQ**2)
    cp_if = (L1_FREQ**2 * wlen_L1 * cp_l1 - L2_FREQ**2 * wlen_L2 * cp_l2) / (
        L1_FREQ**2 - L2_FREQ**2
    )
    amb_iono = (cp_if - pr_if) / (
        (L1_FREQ**2) / (L1_FREQ**2 - L2_FREQ**2) * wlen_L1
        + (L2_FREQ**2) / (L1_FREQ**2 - L2_FREQ**2) * wlen_L2
    )
    return time, amb_iono


def plot_ambiguity_single_sat_single_rec(rnxobs, satname: str):
    pr_l1 = rnxobs["C1C"].sel(sv=satname)
    cp_l1 = rnxobs["L1C"].sel(sv=satname)
    pr_l2 = rnxobs["C2X"].sel(sv=satname)
    cp_l2 = rnxobs["L2X"].sel(sv=satname)
    time = rnxobs.time
    # Wide-lane (phase): L1 - L2
    wl_cp = cp_l1 - cp_l2
    # Narrow-lane (code): L1 + L2
    nl_pr = (
        L1_FREQ / (L1_FREQ + L2_FREQ) * pr_l1 + L2_FREQ / (L1_FREQ + L2_FREQ) * pr_l2
    )

    amb_wl = wl_cp - nl_pr / wl_wlen
    # Use the time-average of the wide-lane ambiguity in downstream computation
    amb_wl_mean = float(amb_wl.mean().values)

    # Narrow-lane (phase): L1 + L2
    # nl_cp = cp_l1 + cp_l2
    # wide-lane (code): L1 - L2
    # wl_pr = (
    #    L1_FREQ / (L1_FREQ - L2_FREQ) * pr_l1 + L2_FREQ / (L1_FREQ - L2_FREQ) * pr_l2
    # )

    # Iono-free combination
    pr_if = (L1_FREQ**2 * pr_l1 - L2_FREQ**2 * pr_l2) / (L1_FREQ**2 - L2_FREQ**2)
    cp_if = (L1_FREQ**2 * wlen_L1 * cp_l1 - L2_FREQ**2 * wlen_L2 * cp_l2) / (
        L1_FREQ**2 - L2_FREQ**2
    )
    amb_n1 = (
        cp_if
        - pr_if
        - (-(L2_FREQ**2)) / (L1_FREQ**2 - L2_FREQ**2) * wlen_L2 * amb_wl_mean
    ) / (
        (L1_FREQ**2) / (L1_FREQ**2 - L2_FREQ**2) * wlen_L1
        + (L2_FREQ**2) / (L1_FREQ**2 - L2_FREQ**2) * wlen_L2
    )

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    axes[0].set_title(r"Wide-lane Ambiguity $N_{L1} - N_{L2}$")
    axes[0].plot(time, wl_cp - nl_pr / wl_wlen)
    axes[0].set_ylabel(r"$B_{wl}$ [cycle]")

    axes[1].set_title(r"Ambiguity $N_{L1}$")
    axes[1].plot(time, amb_n1)
    axes[1].set_ylabel("Ambiguity $N_{L1}$ [cycle]")

    axes[2].set_title("Signal Strength")
    axes[2].plot(time, rnxobs["S1C"].sel(sv=satname), label="S1C")
    axes[2].plot(time, rnxobs["S2X"].sel(sv=satname), label="S2X")
    axes[2].set_ylabel("C/N0 [dB-Hz]")
    axes[2].legend()
    for ax in axes:
        ax.grid(True)
    axes[2].set_xlabel("GPST")
    axes[2].set_xlim(time[0], time[-1])
    fig.suptitle(f"Satellite {satname}", y=1.02)
    plt.tight_layout()
    return fig, axes


def plot_ambiguity_diff(rnxobs, satname1: str, satname2: str):
    time = rnxobs.time

    # Wide-lane combination
    _, amb_sat1_wl = get_wineline_ambiguity(rnxobs, satname1)
    _, amb_sat2_wl = get_wineline_ambiguity(rnxobs, satname2)
    amb_sat1_wl_mean = float(amb_sat1_wl.mean().values)
    amb_sat2_wl_mean = float(amb_sat2_wl.mean().values)

    # Iono-free combination
    _, amb_sat1_n1 = get_narrowline_ambiguity(rnxobs, satname1, amb_sat1_wl_mean)
    _, amb_sat2_n1 = get_narrowline_ambiguity(rnxobs, satname2, amb_sat2_wl_mean)

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    axes[0].set_title(r"Wide-lane Ambiguity $N_{L1} - N_{L2}$")
    axes[0].plot(time, amb_sat1_wl - amb_sat2_wl)
    axes[0].set_ylabel(r"$B_{wl}$ [cycle]")

    axes[1].set_title(r"Ambiguity $N_{L1}$")
    axes[1].plot(time, amb_sat1_n1 - amb_sat2_n1)
    axes[1].set_ylabel("Ambiguity $N_{L1}$ [cycle]")

    axes[2].set_title("Signal Strength")
    axes[2].plot(time, rnxobs["S1C"].sel(sv=satname1), label=f"{satname1} S1C")
    axes[2].plot(time, rnxobs["S2X"].sel(sv=satname1), label=f"{satname1} S2X")
    axes[2].plot(time, rnxobs["S1C"].sel(sv=satname2), label=f"{satname2} S1C")
    axes[2].plot(time, rnxobs["S2X"].sel(sv=satname2), label=f"{satname2} S2X")
    axes[2].set_ylabel("C/N0 [dB-Hz]")
    axes[2].legend()
    for ax in axes:
        ax.grid(True)
    axes[2].set_xlabel("GPST")
    axes[2].set_xlim(time[0], time[-1])

    return fig, axes


def plot_ambiguity_diff2(rnxobs1, rnxobs2, satname1: str, satname2: str):
    # Wide-lane combination
    _, amb_sat1_rec1_wl = get_wineline_ambiguity(rnxobs1, satname1)
    _, amb_sat2_rec1_wl = get_wineline_ambiguity(rnxobs1, satname2)
    _, amb_sat1_rec2_wl = get_wineline_ambiguity(rnxobs2, satname1)
    _, amb_sat2_rec2_wl = get_wineline_ambiguity(rnxobs2, satname2)
    amb_wl_sat12_rec12 = (amb_sat1_rec1_wl - amb_sat2_rec1_wl) - (
        amb_sat1_rec2_wl - amb_sat2_rec2_wl
    )

    # Iono-free combination
    _, amb_sat1_rec1_iono = get_ionospheric_ambiguity(rnxobs1, satname1)
    _, amb_sat2_rec1_iono = get_ionospheric_ambiguity(rnxobs1, satname2)
    _, amb_sat1_rec2_iono = get_ionospheric_ambiguity(rnxobs2, satname1)
    _, amb_sat2_rec2_iono = get_ionospheric_ambiguity(rnxobs2, satname2)
    amb_iono_sat12_rec12 = (amb_sat1_rec1_iono - amb_sat2_rec1_iono) - (
        amb_sat1_rec2_iono - amb_sat2_rec2_iono
    )

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    axes[0].set_title(
        r"Wide-lane Ambiguity Difference between two receivers $N_{L1} - N_{L2}$"
    )
    axes[0].plot(
        rnxobs1.time,
        amb_wl_sat12_rec12,
        ".",
        label=f"Sat {satname1} - Sat {satname2} Rec1 - Rec2",
    )
    axes[0].axhline(
        np.mean(amb_wl_sat12_rec12), color="gray", linestyle="--", label="Mean"
    )
    axes[0].axhline(
        np.round(np.mean(amb_wl_sat12_rec12)),
        color="gray",
        linestyle="--",
        label="Nearest Integer",
    )
    axes[0].set_ylabel(r"$\Delta B_{wl}$ [cycle]")

    axes[1].set_title(r"Iono-free Ambiguity Difference between two receivers $N_{L1}$")
    axes[1].plot(
        rnxobs1.time,
        amb_iono_sat12_rec12 / iono_wlen,
        ".",
        label=f"Sat {satname1} - Sat {satname2} Rec1 - Rec2",
    )
    axes[1].axhline(
        np.mean(amb_iono_sat12_rec12) / iono_wlen,
        color="gray",
        linestyle="--",
        label="Mean",
    )
    axes[1].set_ylabel(r"$\Delta B_{iono}$ [cycle]")

    axes[2].set_title("Signal Strength")
    for signal_name in ["S1C", "S2X"]:
        axes[2].plot(
            rnxobs1.time,
            rnxobs1[signal_name].sel(sv=satname1),
            label=f"{satname1} {signal_name}",
        )
        axes[2].plot(
            rnxobs1.time,
            rnxobs1[signal_name].sel(sv=satname2),
            label=f"{satname2} {signal_name}",
        )
    axes[2].set_ylabel("C/N0 [dB-Hz]")
    axes[2].legend(loc="upper right", fontsize="small")
    for ax in axes:
        ax.grid(True)
    axes[2].set_xlabel("GPST")
    axes[2].set_xlim(rnxobs1.time[0], rnxobs1.time[-1])
    return fig, axes


def main():
    parser = argparse.ArgumentParser(
        description="Plot pseudorange and carrier phase from a RINEX observation file."
    )
    parser.add_argument(
        "infile1",
        help="Path to RINEX observation file (e.g., *.o, *.##o)",
    )
    parser.add_argument(
        "infile2",
        help="Path to RINEX observation file (e.g., *.o, *.##o)",
    )
    parser.add_argument(
        "-o",
        "--outdir",
        default="./outfigs/",
        help="Directory to write output figure files (default: ./outfigs)",
    )
    args = parser.parse_args()

    infile1 = Path(args.infile1)
    if not infile1.is_file():
        raise FileNotFoundError(f"RINEX observation file not found: {infile1}")

    warnings.simplefilter("ignore", FutureWarning)
    rnxobs1 = gr.load(str(infile1))
    print(rnxobs1)

    infile2 = Path(args.infile2)
    if not infile2.is_file():
        raise FileNotFoundError(f"RINEX observation file not found: {infile2}")

    warnings.simplefilter("ignore", FutureWarning)
    rnxobs2 = gr.load(str(infile2))
    print(rnxobs2)

    output_figdir = Path(args.outdir)
    output_figdir.mkdir(parents=True, exist_ok=True)
    Path(output_figdir / "single").mkdir(parents=True, exist_ok=True)
    Path(output_figdir / "diff").mkdir(parents=True, exist_ok=True)
    Path(output_figdir / "diffdiff").mkdir(parents=True, exist_ok=True)

    # target satellite and initial observables plot
    # Derive GPS satellites present in the file (sv starting with 'G')
    try:
        sv_values = [str(s) for s in rnxobs1.sv.values + rnxobs2.sv.values]
        sv_values = list(set(sv_values))
    except Exception:
        # Fallback in case .sv isn't a standard coordinate for some reason
        sv_values = [str(s) for s in rnxobs1.coords.get("sv", []).values]

    satname_list = sorted(
        [s for s in sv_values if s.startswith("G")],
        key=lambda x: (x[0], int(x[1:]) if x[1:].isdigit() else 999),
    )
    logger.info(f"Detected GPS satellites: {satname_list}")
    satname_pari_list = [
        ("G10", "G12"),
        ("G12", "G23"),
        ("G23", "G10"),
        ("G23", "G24"),
        ("G24", "G25"),
        ("G25", "G23"),
    ]

    for satname1, satname2 in satname_pari_list:
        fig, axes = plot_ambiguity_diff(rnxobs1, satname1, satname2)
        out_figfile = (
            output_figdir
            / "diff"
            / f"ambiguity_diff_rec1_{satname1}_{satname2}_L1_L2.png"
        )
        fig.suptitle(f"Satellite Single Difference {satname1} vs {satname2}")
        fig.tight_layout(rect=[0, 0.03, 1, 0.95])
        fig.savefig(out_figfile)
        logger.info(f"{out_figfile}")

        fig, axes = plot_ambiguity_diff(rnxobs2, satname1, satname2)
        out_figfile = (
            output_figdir
            / "diff"
            / f"ambiguity_diff_rec2_{satname1}_{satname2}_L1_L2.png"
        )
        fig.suptitle(f"Satellite Single Difference {satname1} vs {satname2}")
        fig.savefig(out_figfile)
        logger.info(f"{out_figfile}")

        fig, axes = plot_ambiguity_diff2(rnxobs1, rnxobs2, satname1, satname2)
        out_figfile = (
            output_figdir
            / "diffdiff"
            / f"ambiguity_diffdiff_{satname1}_{satname2}_L1_L2.png"
        )
        fig.suptitle(f"Satellite Single Difference {satname1} vs {satname2}")
        fig.savefig(out_figfile)
        logger.info(f"{out_figfile}")

    for satname in satname_list:
        logger.info(f"{satname}")

        fig, axes = plot_ambiguity_single_sat_single_rec(rnxobs1, satname)
        out_figfile = (
            output_figdir / "single" / f"wide_narrow_lane_1_{satname}_L1_L2.png"
        )
        fig.savefig(out_figfile)

        fig, axes = plot_ambiguity_single_sat_single_rec(rnxobs2, satname)
        out_figfile = (
            output_figdir / "single" / f"wide_narrow_lane_2_{satname}_L1_L2.png"
        )
        fig.savefig(out_figfile)
        plt.close("all")

    # Only show interactively when not using headless Agg backend
    if mpl.get_backend() != "Agg":
        plt.show()


if __name__ == "__main__":
    main()
