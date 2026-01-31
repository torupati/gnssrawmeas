"""
Plot Pseudorange and carrier phase from RINEX observation file.
"""

import json
from pathlib import Path
import argparse
import warnings
from logging import getLogger, basicConfig, INFO

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

import georinex as gr
from georinex import rinexobs

from app.gnss.plot.observables import (
    plot_observables,
    plot_pr_cp,
    plot_ambiguity_single_sat_single_rec,
    plot_ionofree_combination,
)

from app.gnss.satellite_signals import (
    get_available_signal_code,
    get_multifrequency_measurements,
)

logger = getLogger(__name__)
basicConfig(level=INFO, format="%(asctime)s %(levelname)s %(message)s")


def print_satellites_per_epoch(rnxobs: rinexobs, constellation_prefix: str = "G"):
    """
    Print the list of GPS satellites for each epoch (time).

    Args:
        rnxobs: RINEX observation data (georinex rinexobs object)
        constellation_prefix: Prefix for the constellation to filter (default: 'G' for GPS)
    """
    # Get all satellite list
    sv_values = [str(s) for s in rnxobs.sv.values]
    l1_obs_code, l2_obs_code = None, None

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
        _visible_satellites = []
        for sv in _satellites:
            if l1_obs_code is None:
                l1_obs_code = get_available_signal_code(rnxobs, sv, "L1")
            if l2_obs_code is None:
                l2_obs_code = get_available_signal_code(rnxobs, sv, "L2")
            if f"S1{l1_obs_code}" in rnxobs:
                strength = float(
                    rnxobs[f"S1{l1_obs_code}"].sel(sv=sv, time=time_val).values
                )
                if np.isnan(strength):
                    continue  # No data for this satellite at this epoch
            _visible_satellites.append(sv)
        time_str = str(time_val)
        if _visible_satellites:
            print(
                f"Epoch {time_idx + 1:4d} | {time_str} | Satellites: {', '.join(_visible_satellites)} (total: {len(_visible_satellites)})"
            )
        else:
            print(f"Epoch {time_idx + 1:4d} | {time_str} | No satellites")
    print("=" * 80)
    print(f"Total epochs: {len(rnxobs.time.values)}")
    print(f"Total satellites in file: {len(_satellites)}")
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
        help="Print satellites visible at each epoch and exit (no plots)",
    )
    parser.add_argument(
        "--start-time",
        default=None,
        help="Start time for data filtering (e.g., '2023-01-19T00:00:00' or '2023-01-19')",
    )
    parser.add_argument(
        "--end-time",
        default=None,
        help="End time for data filtering (e.g., '2023-01-19T23:59:59' or '2023-01-19')",
    )
    args = parser.parse_args()

    infile = Path(args.infile)
    if not infile.is_file():
        raise FileNotFoundError(f"RINEX observation file not found: {infile}")

    warnings.simplefilter("ignore", FutureWarning)
    logger.info("Loading RINEX observation file: %s", infile)
    rnxobs = gr.load(str(infile))
    logger.info(
        "Loaded RINEX observation file with %d epochs and %d satellites",
        len(rnxobs.time.values),
        len(rnxobs.sv.values),
    )

    # Filter by time range if specified
    if args.start_time or args.end_time:
        original_epochs = len(rnxobs.time.values)
        start_time = np.datetime64(args.start_time) if args.start_time else None
        end_time = np.datetime64(args.end_time) if args.end_time else None

        if start_time and end_time:
            rnxobs = rnxobs.sel(time=slice(start_time, end_time))
            logger.info("Filtered data from %s to %s", start_time, end_time)
        elif start_time:
            rnxobs = rnxobs.sel(time=slice(start_time, None))
            logger.info("Filtered data from %s onwards", start_time)
        elif end_time:
            rnxobs = rnxobs.sel(time=slice(None, end_time))
            logger.info("Filtered data up to %s", end_time)

        filtered_epochs = len(rnxobs.time.values)
        logger.info(
            "Epochs after filtering: %d (removed %d)",
            filtered_epochs,
            original_epochs - filtered_epochs,
        )

    # --list-epochs option to print GPS satellites per epoch. Terminate after printing.
    if args.list_epochs:
        print_satellites_per_epoch(rnxobs, constellation_prefix=args.constellation)
        _data = get_multifrequency_measurements(
            rnxobs, constellation_prefix=args.constellation
        )
        with open(
            infile.stem + f"_{args.constellation}_satellites_per_epoch.json", "w"
        ) as f:
            json.dump({"file": str(infile), "data": _data}, f, indent=4, default=str)
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
    logger.info("Detected %s satellites: %s", args.constellation, satname_list)
    for satname in satname_list:
        logger.info("%s processing... output figures to %s", satname, output_figdir)
        out_figfile = output_figdir / f"observables_{satname}.png"
        fig, axes = plot_observables(rnxobs, satname, outfile=out_figfile)
        plt.close(fig)
        logger.debug("Saved %s", out_figfile)

        fig, _ = plot_pr_cp(rnxobs, satname, freq="L1")
        if fig is not None:
            out_figfile = output_figdir / f"bias_analysis_L1_{satname}_L1.png"
            fig.savefig(out_figfile)
            plt.close(fig)
            logger.debug("Saved %s", out_figfile)
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
                "Skipped L5 analysis for %s (no L5 signal available)", satname
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
