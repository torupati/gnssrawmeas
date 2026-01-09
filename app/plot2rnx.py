"""
Plot Pseudorange and carrier phase from RINEX observation file.
"""

from pathlib import Path
import argparse
import georinex as gr
from georinex import rinexobs
import warnings
from logging import getLogger, basicConfig, INFO

import numpy as np
import matplotlib.pyplot as plt
from app.gnss.constants import (
    wlen_L1,
    wlen_L2,
    wlen_L5,
    wl_wlen,
    nl_wlen,
    iono_wlen,
)
from app.gnss.ambiguity import (
    get_wineline_ambiguity,
    get_narrowline_ambiguity,
    get_ionospheric_ambiguity,
)
from app.gnss.satellite_signals import (
    get_satellite_pairs_by_signal_strength,
)

logger = getLogger(__name__)
basicConfig(level=INFO, format="%(asctime)s %(levelname)s %(message)s")

logger.info(f"wlen_L1: {wlen_L1}, wlen_L2: {wlen_L2}, wlen_L5: {wlen_L5}")

logger.info(f"wl_wlen: {wl_wlen}, nl_wlen: {nl_wlen} iono_wlen: {iono_wlen}")


def plot_ambiguity_diff(rnxobs: rinexobs, satname1: str, satname2: str):
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


def plot_ambiguity_diff2(
    rnxobs1: rinexobs, rnxobs2: rinexobs, satname1: str, satname2: str
):
    """Plot ambiguity difference between two receivers and two satellites.

    Args:
        rnxobs1 (rinexobs): GNSS observation data from receiver 1
        rnxobs2 (rinexobs): GNSS observation data from receiver 2
        satname1 (str): Satellite name 1
        satname2 (str): Satellite name 2

    Returns:
        _type_: _description_
    """
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
    parser.add_argument(
        "--constellation",
        choices=["G", "R", "E", "C", "J", "S", "I", "L"],
        default="G",
        help=(
            "Constellation type to include by prefix (e.g., G for GPS, R for GLONASS, E for Galileo, C for BeiDou, J for QZSS)."
        ),
    )
    args = parser.parse_args()

    infile1 = Path(args.infile1)
    if not infile1.is_file():
        raise FileNotFoundError(f"RINEX observation file not found: {infile1}")

    warnings.simplefilter("ignore", FutureWarning)
    rnxobs1: rinexobs = gr.load(str(infile1))
    logger.debug(f"rnxobs1: {rnxobs1}")

    infile2 = Path(args.infile2)
    if not infile2.is_file():
        raise FileNotFoundError(f"RINEX observation file not found: {infile2}")

    warnings.simplefilter("ignore", FutureWarning)
    rnxobs2: rinexobs = gr.load(str(infile2))
    logger.debug(f"rnxobs2: {rnxobs2}")

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
    except ValueError:
        # Fallback in case .sv isn't a standard coordinate for some reason
        sv_values = [str(s) for s in rnxobs1.coords.get("sv", []).values]

    constelation_type = args.constellation
    satname_list = sorted(
        [s for s in sv_values if s.startswith(constelation_type)],
        key=lambda x: (x[0], int(x[1:]) if x[1:].isdigit() else 999),
    )
    if not satname_list:
        raise ValueError("No GPS satellites found in the provided RINEX files.")
    logger.info(f"Detected satellites ({constelation_type}): {satname_list}")

    satellite_pair = get_satellite_pairs_by_signal_strength(
        rnxobs1,
        signal_type="S1C",
        constellation=constelation_type,
        top_n=6,
    )
    if not satellite_pair:
        raise ValueError("No satellite pairs could be formed based on signal strength.")
    logger.info(f"Satellite pairs selected for analysis: {satellite_pair}")
    satname_pari_list = satellite_pair

    # satname_pari_list = [
    #    ("G10", "G12"),
    #    ("G12", "G23"),
    #    ("G23", "G10"),
    #    ("G23", "G24"),
    #    ("G24", "G25"),
    #    ("G25", "G23"),
    # ]
    # satname_pari_list = [("J02", "J03"), ("J03", "J07"), ("J07", "J02")]  # QZSS

    for satname1, satname2 in satname_pari_list:
        logger.info(f"Processing satellite pair: {satname1}, {satname2}")
        if satname1 not in [str(s) for s in rnxobs1.sv.values]:
            logger.warning(f"Satellite {satname1} not found in infile1. Skipping.")
            continue
        if satname2 not in [str(s) for s in rnxobs1.sv.values]:
            logger.warning(f"Satellite {satname2} not found in infile1. Skipping.")
            continue
        if satname1 not in [str(s) for s in rnxobs2.sv.values]:
            logger.warning(f"Satellite {satname1} not found in infile2. Skipping.")
            continue
        if satname2 not in [str(s) for s in rnxobs2.sv.values]:
            logger.warning(f"Satellite {satname2} not found in infile2. Skipping.")
            continue

        fig, axes = plot_ambiguity_diff(rnxobs1, satname1, satname2)
        out_figfile = (
            output_figdir
            / "diff"
            / f"ambiguity_diff_rec1_{satname1}_{satname2}_L1_L2.png"
        )
        fig.suptitle(f"Satellite Single Difference {satname1} vs {satname2}")
        fig.tight_layout(rect=(0, 0.03, 1, 0.95))
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

    # Only show interactively when not using headless Agg backend
    # if mpl.get_backend() != "Agg":
    #    plt.show()
    plt.close("all")


if __name__ == "__main__":
    main()
