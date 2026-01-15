"""
Plot Pseudorange and carrier phase from RINEX observation file.
"""

from pathlib import Path
import argparse
import warnings
from logging import getLogger, basicConfig, INFO

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

import georinex as gr
from georinex import rinexobs

from app.gnss.ambiguity import (
    get_wineline_ambiguity,
    get_narrowline_ambiguity,
)
from app.gnss.constants import (
    CLIGHT,
    L1_FREQ,
    L2_FREQ,
    wlen_L1,
    wlen_L2,
    wlen_L5,
)

logger = getLogger(__name__)
basicConfig(level=INFO, format="%(asctime)s %(levelname)s %(message)s")


def get_available_signal_code(rnxobs, satname: str, freq_prefix: str):
    """
    Get available signal code for a given frequency prefix (e.g., 'L5', 'L2', 'L1').
    Returns the signal code suffix (e.g., 'X', 'I', 'Q', 'C') if available.

    Args:
        rnxobs: RINEX observation data
        satname: Satellite name (e.g., 'G01')
        freq_prefix: Frequency prefix (e.g., 'L5', 'L2', 'L1')

    Returns:
        Signal code suffix (e.g., 'X', 'I', 'Q') or None if not available
    """
    # Check available observation types
    available_obs = list(rnxobs.data_vars)

    # Find carrier phase observations starting with the frequency prefix
    carrier_phases = [obs for obs in available_obs if obs.startswith(freq_prefix)]

    if not carrier_phases:
        return None

    # Priority order for signal codes (prefer I, then X, then Q, then others)
    priority_codes = ["I", "X", "Q", "C"]

    # First, try priority codes
    for code in priority_codes:
        cp_obs = f"{freq_prefix}{code}"
        if cp_obs in carrier_phases:
            try:
                data = rnxobs[cp_obs].sel(sv=satname)
                if not data.isnull().all():
                    # Extract frequency number (e.g., '5' from 'L5')
                    freq_num = freq_prefix[1:]

                    # Check if corresponding pseudorange and doppler exist
                    pr_obs = f"C{freq_num}{code}"
                    dp_obs = f"D{freq_num}{code}"

                    if pr_obs in available_obs and dp_obs in available_obs:
                        return code
            except (KeyError, ValueError):
                continue

    # If no priority code works, try any available carrier phase
    for cp_obs in carrier_phases:
        try:
            data = rnxobs[cp_obs].sel(sv=satname)
            if not data.isnull().all():
                signal_code = cp_obs[len(freq_prefix) :]
                freq_num = freq_prefix[1:]

                pr_obs = f"C{freq_num}{signal_code}"
                dp_obs = f"D{freq_num}{signal_code}"

                if pr_obs in available_obs and dp_obs in available_obs:
                    return signal_code
        except (KeyError, ValueError):
            continue

    return None


def plot_observables(rnxobs, satname: str, outfile: str = "obs.png"):
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
    fig.tight_layout()
    fig.savefig(outfile)
    return fig, axes


def plot_pr_cp(rnxobs, satname: str, freq=""):
    if freq == "L1":
        wlen = wlen_L1
        # Dynamically detect available L1 signal code
        signal_code = get_available_signal_code(rnxobs, satname, "L1")
        if signal_code is None:
            logger.warning(
                f"No L1 signal available for {satname}, skipping L1 analysis"
            )
            return None, None
        logger.info(f"Using L1{signal_code} signal for {satname}")
        cp = rnxobs[f"L1{signal_code}"].sel(sv=satname)
        pr = rnxobs[f"C1{signal_code}"].sel(sv=satname)
        dp = rnxobs[f"D1{signal_code}"].sel(sv=satname)
    elif freq == "L2":
        wlen = wlen_L2
        # Dynamically detect available L2 signal code
        signal_code = get_available_signal_code(rnxobs, satname, "L2")
        if signal_code is None:
            logger.warning(
                f"No L2 signal available for {satname}, skipping L2 analysis"
            )
            return None, None
        logger.info(f"Using L2{signal_code} signal for {satname}")
        cp = rnxobs[f"L2{signal_code}"].sel(sv=satname)
        pr = rnxobs[f"C2{signal_code}"].sel(sv=satname)
        dp = rnxobs[f"D2{signal_code}"].sel(sv=satname)
    elif freq == "L5":
        wlen = wlen_L5
        # Dynamically detect available L5 signal code
        signal_code = get_available_signal_code(rnxobs, satname, "L5")
        if signal_code is None:
            logger.warning(
                f"No L5 signal available for {satname}, skipping L5 analysis"
            )
            return None, None
        logger.info(f"Using L5{signal_code} signal for {satname}")
        cp = rnxobs[f"L5{signal_code}"].sel(sv=satname)
        pr = rnxobs[f"C5{signal_code}"].sel(sv=satname)
        dp = rnxobs[f"D5{signal_code}"].sel(sv=satname)
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
    fig.suptitle(f"Analysis of Raw Measurement ({satname})")
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    return fig, axes


def plot_ionofree_combination(rnxobs, satname: str):
    # Dynamically detect available L1 signal code
    l1_signal_code = get_available_signal_code(rnxobs, satname, "L1")
    if l1_signal_code is None:
        logger.warning(
            f"No L1 signal available for {satname}, cannot compute iono-free combination"
        )
        return None, None

    # Dynamically detect available L2 signal code
    l2_signal_code = get_available_signal_code(rnxobs, satname, "L2")
    if l2_signal_code is None:
        logger.warning(
            f"No L2 signal available for {satname}, cannot compute iono-free combination"
        )
        return None, None

    logger.info(
        f"Computing iono-free combination using L1{l1_signal_code} and L2{l2_signal_code} for {satname}"
    )

    pr_l1 = rnxobs[f"C1{l1_signal_code}"].sel(sv=satname)
    cp_l1 = rnxobs[f"L1{l1_signal_code}"].sel(sv=satname)
    pr_l2 = rnxobs[f"C2{l2_signal_code}"].sel(sv=satname)
    cp_l2 = rnxobs[f"L2{l2_signal_code}"].sel(sv=satname)
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
    axes[2].plot(
        time, rnxobs[f"S1{l1_signal_code}"].sel(sv=satname), label=f"S1{l1_signal_code}"
    )
    axes[2].plot(
        time, rnxobs[f"S2{l2_signal_code}"].sel(sv=satname), label=f"S2{l2_signal_code}"
    )
    axes[2].set_ylabel("C/N0 [dB-Hz]")
    axes[2].legend()
    for ax in axes:
        ax.grid(True)
    axes[2].set_xlabel("GPST")
    axes[2].set_xlim(time[0], time[-1])
    fig.tight_layout()
    return fig, axes


def plot_ambiguity_single_sat_single_rec(rnxobs: rinexobs, satname: str):
    # Dynamically detect available L1 signal code
    l1_signal_code = get_available_signal_code(rnxobs, satname, "L1")
    if l1_signal_code is None:
        logger.warning(
            f"No L1 signal available for {satname}, cannot compute ambiguity"
        )
        return None, None

    # Dynamically detect available L2 signal code
    l2_signal_code = get_available_signal_code(rnxobs, satname, "L2")
    if l2_signal_code is None:
        logger.warning(
            f"No L2 signal available for {satname}, cannot compute ambiguity"
        )
        return None, None

    logger.info(
        f"Computing ambiguity using L1{l1_signal_code} and L2{l2_signal_code} for {satname}"
    )

    time = rnxobs.time
    _, amb_wl = get_wineline_ambiguity(rnxobs, satname, l1_signal_code, l2_signal_code)
    # Use the time-average of the wide-lane ambiguity in downstream computation
    amb_wl_mean = float(amb_wl.mean().values)

    # Iono-free combination
    _, amb_n1 = get_narrowline_ambiguity(
        rnxobs, satname, amb_wl_mean, l1_signal_code, l2_signal_code
    )

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    axes[0].set_title(r"Wide-lane Ambiguity $N_{L1} - N_{L2}$")
    axes[0].plot(time, amb_wl)
    axes[0].set_ylabel(r"$B_{wl}$ [cycle]")

    axes[1].set_title(r"Ambiguity $N_{L1}$")
    axes[1].plot(time, amb_n1)
    axes[1].set_ylabel("Ambiguity $N_{L1}$ [cycle]")

    axes[2].set_title("Signal Strength")
    axes[2].plot(
        time, rnxobs[f"S1{l1_signal_code}"].sel(sv=satname), label=f"S1{l1_signal_code}"
    )
    axes[2].plot(
        time, rnxobs[f"S2{l2_signal_code}"].sel(sv=satname), label=f"S2{l2_signal_code}"
    )
    axes[2].set_ylabel("C/N0 [dB-Hz]")
    axes[2].legend()
    for ax in axes:
        ax.grid(True)
    axes[2].set_xlabel("GPST")
    axes[2].set_xlim(time[0], time[-1])
    fig.suptitle(f"Satellite {satname}", y=1.02)
    plt.tight_layout()
    return fig, axes


def print_gps_satellites_per_epoch(rnxobs: rinexobs, constellation_prefix: str = "G"):
    """
    Print the list of GPS satellites for each epoch (time).

    Args:
        rnxobs: RINEX observation data (georinex rinexobs object)
        constellation_prefix: Prefix for the constellation to filter (default: 'G' for GPS)
    """
    # Get all satellite list
    sv_values = [str(s) for s in rnxobs.sv.values]

    # Filter GPS satellites only (satellites starting with 'G')
    _satellites = sorted(
        [s for s in sv_values if s.startswith(constellation_prefix)],
        key=lambda x: int(x[1:]) if x[1:].isdigit() else 999,
    )

    print("\n" + "=" * 80)
    print(f"{constellation_prefix} Satellites per Epoch")
    print("=" * 80)

    # Process each epoch
    for time_idx, time_val in enumerate(rnxobs.time.values):
        # Check GPS satellites observed at this epoch
        visible_sats = []

        for sv in _satellites:
            try:
                # Check S1C signal strength (to verify data exists)
                if "S1C" in rnxobs:
                    strength = float(rnxobs["S1C"].sel(sv=sv, time=time_val).values)
                    if not np.isnan(strength):
                        visible_sats.append(sv)
                # If S1C is not available, try other signals
                elif "C1C" in rnxobs:
                    data = float(rnxobs["C1C"].sel(sv=sv, time=time_val).values)
                    if not np.isnan(data):
                        visible_sats.append(sv)
            except (KeyError, ValueError):
                continue

        # Print time and GPS satellite list
        time_str = str(time_val)
        if visible_sats:
            print(
                f"Epoch {time_idx + 1:4d} | {time_str} | GPS satellites: {', '.join(visible_sats)} (total: {len(visible_sats)})"
            )
        else:
            print(f"Epoch {time_idx + 1:4d} | {time_str} | No GPS satellites")

    print("=" * 80)
    print(f"Total epochs: {len(rnxobs.time.values)}")
    print(f"Total GPS satellites in file: {len(_satellites)}")
    print("=" * 80 + "\n")


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
    parser.add_argument(
        "--constellation",
        choices=["G", "R", "E", "C", "J", "S", "I", "L"],
        default="G",
        help=(
            "Constellation type to include by prefix (e.g., G for GPS, R for GLONASS, E for Galileo, C for BeiDou, J for QZSS)."
        ),
    )
    parser.add_argument(
        "--list-epochs",
        action="store_true",
        help="Print GPS satellites visible at each epoch and exit (no plots)",
    )
    args = parser.parse_args()

    infile = Path(args.infile)
    if not infile.is_file():
        raise FileNotFoundError(f"RINEX observation file not found: {infile}")

    warnings.simplefilter("ignore", FutureWarning)
    logger.info(f"Loading RINEX observation file: {infile}")
    rnxobs = gr.load(str(infile))
    logger.info(
        f"Loaded RINEX observation file with {len(rnxobs.time.values)} epochs and {len(rnxobs.sv.values)} satellites"
    )

    # --list-epochs option to print GPS satellites per epoch. Terminate after printing.
    if args.list_epochs:
        print_gps_satellites_per_epoch(rnxobs, constellation_prefix=args.constellation)
        return

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
        [s for s in sv_values if s.startswith(args.constellation)],
        key=lambda x: (x[0], int(x[1:]) if x[1:].isdigit() else 999),
    )
    logger.info(f"Detected {args.constellation} satellites: {satname_list}")
    for satname in satname_list:
        logger.info(f"{satname} processing... output figures to {output_figdir}")
        out_figfile = output_figdir / f"observables_{satname}.png"
        fig, axes = plot_observables(rnxobs, satname, outfile=out_figfile)
        plt.close(fig)
        logger.debug(f"Saved {out_figfile}")

        fig, _ = plot_pr_cp(rnxobs, satname, freq="L1")
        if fig is not None:
            out_figfile = output_figdir / f"bias_analysis_L1_{satname}_L1.png"
            fig.savefig(out_figfile)
            plt.close(fig)
            logger.debug(f"Saved {out_figfile}")
        else:
            logger.warning(
                f"Skipped L1 analysis for {satname} (no L1 signal available)"
            )

        fig, _ = plot_pr_cp(rnxobs, satname, freq="L2")
        if fig is not None:
            out_figfile = output_figdir / f"bias_analysis_L2_{satname}_L2.png"
            fig.savefig(out_figfile)
            plt.close(fig)
            logger.debug(f"Saved {out_figfile}")
        else:
            logger.warning(
                f"Skipped L2 analysis for {satname} (no L2 signal available)"
            )

        fig, _ = plot_pr_cp(rnxobs, satname, freq="L5")
        if fig is not None:
            out_figfile = output_figdir / f"bias_analysis_L5_{satname}_L5.png"
            fig.savefig(out_figfile)
            plt.close(fig)
            logger.debug(f"Saved {out_figfile}")
        else:
            logger.warning(
                f"Skipped L5 analysis for {satname} (no L5 signal available)"
            )

        fig, axes = plot_ambiguity_single_sat_single_rec(rnxobs, satname)
        if fig is not None:
            out_figfile = output_figdir / f"wide_narrow_lane_{satname}_L1_L2.png"
            fig.savefig(out_figfile)
            plt.close(fig)
            logger.debug(f"Saved {out_figfile}")
        else:
            logger.warning(
                f"Skipped ambiguity analysis for {satname} (L1 or L2 signal not available)"
            )

        fig, axes = plot_ionofree_combination(rnxobs, satname)
        if fig is not None:
            out_figfile = output_figdir / f"ionofree_combination_{satname}_L1_L2.png"
            fig.savefig(out_figfile)
            plt.close(fig)
            logger.debug(f"Saved {out_figfile}")
        else:
            logger.warning(
                f"Skipped iono-free combination for {satname} (L1 or L2 signal not available)"
            )

    # Only show interactively when not using headless Agg backend
    if mpl.get_backend() != "Agg":
        plt.show()


if __name__ == "__main__":
    main()
