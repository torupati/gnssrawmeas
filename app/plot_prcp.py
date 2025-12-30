"""
Plot Pseudorange and carrier phase from RINEX observation file.

"""

from pathlib import Path
import argparse
import georinex as gr
import warnings
from logging import getLogger, basicConfig, INFO

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


def plot_observables(rnxobs, satname: str, outfile: str = "obs.png"):
    ax = plt.gca()
    ax.plot(rnxobs.time, rnxobs["C1C"].sel(sv=satname))
    ax.set_xlabel("GPS time")
    ax.set_ylabel("Pseudorange [m]")
    ax.grid(True)

    fig, axes = plt.subplots(4, 1, figsize=(10, 8), sharex=True)
    axes[0].plot(rnxobs.time, rnxobs["C1C"].sel(sv=satname), label=satname)
    axes[1].plot(rnxobs.time, rnxobs["L1C"].sel(sv=satname), label=satname)
    axes[2].plot(rnxobs.time, rnxobs["D1C"].sel(sv=satname), label=satname)
    axes[3].plot(rnxobs.time, rnxobs["S1C"].sel(sv=satname), label=satname)

    axes[0].set_title("Pseudo range[m]")
    axes[0].set_ylabel(r"$\rho$ [m]")
    axes[1].set_title("carrier phase")
    axes[1].set_ylabel(r"$\phi$ [cycle]")
    axes[2].set_title("Doppler frequency")
    axes[2].set_ylabel("D[Hz]")
    axes[3].set_title("C/N0")
    axes[3].set_ylabel("S [dB]")
    for a in axes:
        a.grid(True)

    axes[3].set_xlabel("GPST")
    plt.tight_layout()
    plt.savefig(outfile)
    return fig, axes


def plot_pr_cp(rnxobs, satname: str, freq=""):
    if freq == "L1":
        wlen = wlen_L1
        cp = rnxobs["L1C"].sel(sv=satname)
        pr = rnxobs["C1C"].sel(sv=satname)
        dp = rnxobs["D1C"].sel(sv=satname)
    elif freq == "L2":
        wlen = wlen_L2
        cp = rnxobs["L2X"].sel(sv=satname)
        pr = rnxobs["C2X"].sel(sv=satname)
        dp = rnxobs["D2X"].sel(sv=satname)
    elif freq == "L5":
        wlen = wlen_L5
        cp = rnxobs["L5X"].sel(sv=satname)
        pr = rnxobs["C5X"].sel(sv=satname)
        dp = rnxobs["D5X"].sel(sv=satname)
    else:
        raise ValueError("freq must be L1, L2, or L5")
    cp_pr = cp - pr / wlen
    # caluclate doppler - difference of carrier phase
    b2 = cp.diff("time") * (1 / 30.0) + dp

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    plt.suptitle(f"Analysis of Raw Measurement ({satname})")
    axes[0].set_title(r"$-N - \frac{2}{\lambda}I$")
    axes[0].plot(rnxobs.time, cp_pr)
    axes[0].set_ylabel("CP-PR")

    axes[1].set_title(r"$\frac{1}{\lambda}(I + d/dt (I+T))$")
    axes[1].plot(b2.time, b2)
    axes[1].set_ylabel("DP - CP")
    x = cp_pr + 2.0 * b2

    axes[2].set_title(r"$N$")
    axes[2].plot(x.time, -x.values)
    axes[2].set_ylabel("bias [cycle]")
    for ax in axes:
        ax.grid(True)
    axes[2].set_xlabel("GPST")
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    return fig, axes


def plot_ionofree_combination(rnxobs, satname: str):
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
    wlen_if = CLIGHT / (L1_FREQ**2 - L2_FREQ**2) * (L1_FREQ + L2_FREQ)

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    axes[0].set_title("Iono-free Pseudorange and Carrier Phase")
    axes[0].plot(time, pr_if, label="Pseudorange IF")
    axes[0].plot(time, cp_if * wlen_if, label="Carrier Phase IF")
    axes[0].set_ylabel("Pseudorange / Carrier Phase [m]")
    axes[0].legend()

    axes[1].set_title(r"Carrier Phase - Pseudorange")
    axes[1].plot(time, cp_if - pr_if)
    axes[1].set_ylabel("CP - PR [m]")

    axes[2].set_title("Signal Strength")
    axes[2].plot(time, rnxobs["S1C"].sel(sv=satname), label="S1C")
    axes[2].plot(time, rnxobs["S2X"].sel(sv=satname), label="S2X")
    axes[2].set_ylabel("C/N0 [dB-Hz]")
    axes[2].legend()
    for ax in axes:
        ax.grid(True)
    axes[2].set_xlabel("GPST")
    axes[2].set_xlim(time[0], time[-1])
    plt.tight_layout()
    return fig, axes


def plot_ambiguity_single_sat_single_rec(rnxobs, satname: str):
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
    nl_wlen = CLIGHT / (L1_FREQ + L2_FREQ)
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

    logger.debug(f"wide lane {wl_wlen * 100} cm narrow-lane {nl_wlen * 100} cm")

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
    plt.tight_layout()
    return fig, axes


def main():
    parser = argparse.ArgumentParser(
        description="Plot pseudorange and carrier phase from a RINEX observation file."
    )
    parser.add_argument(
        "infile",
        help="Path to RINEX observation file (e.g., *.o, *.##o)",
    )
    parser.add_argument(
        "-o",
        "--outdir",
        default="./outfigs/",
        help="Directory to write output figure files (default: ./outfigs)",
    )
    args = parser.parse_args()

    infile = Path(args.infile)
    if not infile.is_file():
        raise FileNotFoundError(f"RINEX observation file not found: {infile}")

    warnings.simplefilter("ignore", FutureWarning)
    rnxobs = gr.load(str(infile))
    print(rnxobs)

    output_figdir = Path(args.outdir)
    output_figdir.mkdir(parents=True, exist_ok=True)

    # target satellite and initial observables plot
    # Derive GPS satellites present in the file (sv starting with 'G')
    try:
        sv_values = [str(s) for s in rnxobs.sv.values]
    except Exception:
        # Fallback in case .sv isn't a standard coordinate for some reason
        sv_values = [str(s) for s in rnxobs.coords.get("sv", []).values]

    satname_list = sorted(
        [s for s in sv_values if s.startswith("G")],
        key=lambda x: (x[0], int(x[1:]) if x[1:].isdigit() else 999),
    )
    logger.info(f"Detected GPS satellites: {satname_list}")
    for satname in satname_list:
        logger.info(f"{satname}")
        fig, axes = plot_observables(rnxobs, satname, outfile="obs.png")

        fig, axes = plot_pr_cp(rnxobs, satname, freq="L1")
        out_figfile = output_figdir / f"bias_analysis_L1_{satname}_L1.png"
        plt.savefig(out_figfile)

        fig, axes = plot_pr_cp(rnxobs, satname, freq="L2")
        out_figfile = output_figdir / f"bias_analysis_L2_{satname}_L2.png"
        plt.savefig(out_figfile)

        fig, axes = plot_pr_cp(rnxobs, satname, freq="L5")
        out_figfile = output_figdir / f"bias_analysis_L5_{satname}_L5.png"
        plt.savefig(out_figfile)

        fig, axes = plot_ambiguity_single_sat_single_rec(rnxobs, satname)
        out_figfile = output_figdir / f"wide_narrow_lane_{satname}_L1_L2.png"
        plt.savefig(out_figfile)

        fig, axes = plot_ionofree_combination(rnxobs, satname)
        out_figfile = output_figdir / f"ionofree_combination_{satname}_L1_L2.png"
        plt.savefig(out_figfile)
        plt.close("all")

    # Only show interactively when not using headless Agg backend
    if mpl.get_backend() != "Agg":
        plt.show()


if __name__ == "__main__":
    main()
