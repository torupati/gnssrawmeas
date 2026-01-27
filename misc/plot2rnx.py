"""
Plot Pseudorange and carrier phase from RINEX observation file.
"""

from pathlib import Path
import argparse
import json
import georinex as gr
from georinex import rinexobs
import warnings
from logging import getLogger, basicConfig, INFO

import numpy as np
import matplotlib.pyplot as plt
import xarray as xr
from app.gnss.constants import (
    wlen_L1,
    wlen_L2,
    wlen_L5,
    wl_wlen,
    nl_wlen,
    iono_wlen,
)
from app.gnss.ambiguity import (
    get_widelane_ambiguity,
    get_narrowlane_ambiguity,
    calculate_double_difference_widelane_ambiguity,
    calculate_double_difference_ionospheric_ambiguity,
)
from app.gnss.satellite_signals import (
    get_satellite_pairs_by_signal_strength,
    get_available_signal_code,
)

logger = getLogger(__name__)
basicConfig(level=INFO, format="%(asctime)s %(levelname)s %(message)s")

logger.info(f"wlen_L1: {wlen_L1}, wlen_L2: {wlen_L2}, wlen_L5: {wlen_L5}")

logger.info(f"wl_wlen: {wl_wlen}, nl_wlen: {nl_wlen} iono_wlen: {iono_wlen}")


def plot_ambiguity_diff(rnxobs: rinexobs, satname1: str, satname2: str):
    """Plot ambiguity difference between two satellites.
    Args:
        rnxobs (rinexobs): RINEX observation data
        satname1 (str): Satellite name 1
        satname2 (str): Satellite name 2
    Raises:
        ValueError: If suitable signal codes for L1 or L2 cannot be found
    Returns:
        fig, axes: Matplotlib figure and axes objects

    Note:
        This function calculates and plots the wide-lane and iono-free ambiguities
        between two satellites, along with their signal strengths. Differences are calculated in the single observation data, so time axes are the same.
    """
    time = rnxobs.time

    # Wide-lane combination
    _obs_l1_code = get_available_signal_code(rnxobs, satname1, "L1")
    _obs_l2_code = get_available_signal_code(rnxobs, satname1, "L2")
    if _obs_l1_code is None or _obs_l2_code is None:
        raise ValueError(
            f"Cannot find suitable signal codes for L1 or L2 for satellite {satname1}"
        )
    amb_sat1_wl = get_widelane_ambiguity(
        rnxobs,
        satname1,
        f"C1{_obs_l1_code}",
        f"L1{_obs_l1_code}",
        f"C2{_obs_l2_code}",
        f"L2{_obs_l2_code}",
    )
    amb_sat2_wl = get_widelane_ambiguity(
        rnxobs,
        satname2,
        f"C1{_obs_l1_code}",
        f"L1{_obs_l1_code}",
        f"C2{_obs_l2_code}",
        f"L2{_obs_l2_code}",
    )
    amb_sat1_wl_mean = float(amb_sat1_wl.mean().values)
    amb_sat2_wl_mean = float(amb_sat2_wl.mean().values)

    # Iono-free combination
    amb_sat1_n1 = get_narrowlane_ambiguity(
        rnxobs,
        satname1,
        amb_sat1_wl_mean,
        f"C1{_obs_l1_code}",
        f"L1{_obs_l1_code}",
        f"C2{_obs_l2_code}",
        f"L2{_obs_l2_code}",
    )
    amb_sat2_n1 = get_narrowlane_ambiguity(
        rnxobs,
        satname2,
        amb_sat2_wl_mean,
        f"C1{_obs_l1_code}",
        f"L1{_obs_l1_code}",
        f"C2{_obs_l2_code}",
        f"L2{_obs_l2_code}",
    )

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    axes[0].set_title(r"Wide-lane Ambiguity $N_{L1} - N_{L2}$")
    axes[0].plot(time, amb_sat1_wl - amb_sat2_wl)
    axes[0].set_ylabel(r"$B_{wl}$ [cycle]")

    axes[1].set_title(r"Ambiguity $N_{L1}$")
    axes[1].plot(time, amb_sat1_n1 - amb_sat2_n1)
    axes[1].set_ylabel("Ambiguity $N_{L1}$ [cycle]")

    axes[2].set_title("Signal Strength")
    axes[2].plot(
        time,
        rnxobs[f"S1{_obs_l1_code}"].sel(sv=satname1),
        label=f"{satname1} S1{_obs_l1_code}",
    )
    axes[2].plot(
        time,
        rnxobs[f"S2{_obs_l2_code}"].sel(sv=satname1),
        label=f"{satname1} S2{_obs_l2_code}",
    )
    axes[2].plot(
        time,
        rnxobs[f"S1{_obs_l1_code}"].sel(sv=satname2),
        label=f"{satname2} S1{_obs_l1_code}",
    )
    axes[2].plot(
        time,
        rnxobs[f"S2{_obs_l2_code}"].sel(sv=satname2),
        label=f"{satname2} S2{_obs_l2_code}",
    )
    axes[2].set_ylabel("C/N0 [dB-Hz]")
    axes[2].legend()
    for ax in axes:
        ax.grid(True)
    axes[2].set_xlabel("GPST")
    axes[2].set_xlim(time[0], time[-1])

    return fig, axes


def widelane_ambiguity_to_dict(
    amb_wl: xr.DataArray, satname1: str, satname2: str, time_values: np.ndarray
) -> dict:
    """Convert widelane ambiguity data to dictionary format.

    Args:
        amb_wl (xr.DataArray): Widelane ambiguity data
        satname1 (str): Satellite name 1
        satname2 (str): Satellite name 2
        time_values (np.ndarray): Time values array

    Returns:
        dict: Dictionary containing satellite pair, time, ambiguity values, and statistics
    """
    # Ensure we work with a float array and identify valid (non-NaN) entries
    amb_values = np.asarray(amb_wl.values, dtype=float)
    valid_mask = ~np.isnan(amb_values)

    # Only include epochs with valid ambiguity values to avoid NaN in JSON output
    epochs = [
        {"time": str(t), "widelane_ambiguity": float(wl)}
        for t, wl, is_valid in zip(time_values, amb_values, valid_mask)
        if is_valid
    ]

    mean_value = np.nanmean(amb_values)
    std_value = np.nanstd(amb_values)

    return {
        "satellite_pair": [satname1, satname2],
        "epochs": epochs,
        "statistics": {
            "mean": float(mean_value),
            "std": float(std_value),
            "rounded_mean": float(np.round(mean_value)),
        },
    }


def plot_ambiguity_diff2(
    rnxobs1: rinexobs,
    rnxobs2: rinexobs,
    satname1: str,
    satname2: str,
    obs1_l1_code: str = "C",
    obs1_l2_code: str = "X",
    obs2_l1_code: str = "C",
    obs2_l2_code: str = "X",
    time_synchronize: bool = True,
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
    amb_wl_sat12_rec12 = calculate_double_difference_widelane_ambiguity(
        rnxobs1,
        rnxobs2,
        satname1,
        satname2,
        obs1_l1_code,
        obs1_l2_code,
        obs2_l1_code,
        obs2_l2_code,
        time_synchronize,
    )

    # Iono-free combination
    amb_iono_sat12_rec12 = calculate_double_difference_ionospheric_ambiguity(
        rnxobs1,
        rnxobs2,
        satname1,
        satname2,
        obs1_l1_code,
        obs1_l2_code,
        obs2_l1_code,
        obs2_l2_code,
        time_synchronize,
    )

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    axes[0].set_title(
        rf"Wide-lane Ambiguity DD {satname1}-{satname2} $N_{{L1}} - N_{{L2}}$"
    )
    axes[0].plot(
        amb_wl_sat12_rec12.time,
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

    axes[1].set_title(rf"Iono-free Ambiguity DD {satname1}-{satname2} $N_{{L1}}$")
    axes[1].plot(
        amb_iono_sat12_rec12.time,
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
    for signal_name in [f"S1{obs1_l1_code}", f"S2{obs1_l2_code}"]:
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
        choices=["G", "R", "E", "C", "J", "S", "I", "L", "a"],
        default="G",
        help=(
            "Constellation type to include by prefix (e.g., G for GPS, R for GLONASS, E for Galileo, C for BeiDou, J for QZSS, a for all)."
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

    # Prepare output directories
    output_figdir = Path(args.outdir)
    output_figdir.mkdir(parents=True, exist_ok=True)
    Path(output_figdir / "single").mkdir(parents=True, exist_ok=True)
    Path(output_figdir / "diff").mkdir(parents=True, exist_ok=True)
    Path(output_figdir / "diffdiff").mkdir(parents=True, exist_ok=True)

    # target satellite and initial observables plot
    try:
        sv_values = [str(s) for s in rnxobs1.sv.values + rnxobs2.sv.values]
        sv_values = list(set(sv_values))
    except ValueError:
        # Fallback in case .sv isn't a standard coordinate for some reason
        sv_values = [str(s) for s in rnxobs1.coords.get("sv", []).values]

    constellation_type = args.constellation
    if constellation_type == "a":
        satname_list = sorted(
            sv_values,
            key=lambda x: (x[0], int(x[1:]) if x[1:].isdigit() else 999),
        )
    else:
        satname_list = sorted(
            [s for s in sv_values if s.startswith(constellation_type)],
            key=lambda x: (x[0], int(x[1:]) if x[1:].isdigit() else 999),
        )
    if not satname_list:
        raise ValueError("No satellites found in the provided RINEX files.")
    logger.info(f"Detected satellites ({constellation_type}): {satname_list}")

    satellite_pair = get_satellite_pairs_by_signal_strength(
        rnxobs1,
        signal_type="S1C",
        constellation=constellation_type,
        top_n=6,
    )
    if not satellite_pair:
        raise ValueError("No satellite pairs could be formed based on signal strength.")
    logger.info(f"Satellite pairs selected for analysis: {satellite_pair}")
    satname_pair_list = satellite_pair

    for satname1, satname2 in satname_pair_list:
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

        obs1_l1_code = get_available_signal_code(rnxobs1, satname1, "L1")
        obs1_l2_code = get_available_signal_code(rnxobs1, satname1, "L2")
        obs2_l1_code = get_available_signal_code(rnxobs2, satname1, "L1")
        obs2_l2_code = get_available_signal_code(rnxobs2, satname1, "L2")
        if (
            obs1_l1_code is None
            or obs1_l2_code is None
            or obs2_l1_code is None
            or obs2_l2_code is None
        ):
            logger.warning(
                "Cannot find suitable signal codes for L1 or L2 for "
                "satellite %s or %s. Skipping.",
                satname1,
                satname2,
            )
            continue

        # Calculate and save widelane ambiguity to JSON
        amb_wl_sat12_rec12 = calculate_double_difference_widelane_ambiguity(
            rnxobs1,
            rnxobs2,
            satname1,
            satname2,
            obs1_l1_code,
            obs1_l2_code,
            obs2_l1_code,
            obs2_l2_code,
            True,
        )
        widelane_data = widelane_ambiguity_to_dict(
            amb_wl_sat12_rec12, satname1, satname2, rnxobs1.time.values
        )
        json_file = output_figdir / "diffdiff" / f"widelane_{satname1}_{satname2}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(widelane_data, f, indent=2)
        logger.info(f"Widelane data saved to: {json_file}")

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

        fig, axes = plot_ambiguity_diff2(
            rnxobs1,
            rnxobs2,
            satname1,
            satname2,
            obs1_l1_code,
            obs1_l2_code,
            obs2_l1_code,
            obs2_l2_code,
        )
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
