import argparse
from pathlib import Path
from logging import getLogger, basicConfig, INFO

import matplotlib.pyplot as plt

from app.gnss.satellite_signals import (
    EpochObservations,
    parse_rinex_observation_file,
    save_gnss_observations_to_json,
)

logger = getLogger(__name__)


def convert_epochs_to_json(epochs):
    """
    Convert epochs data to JSON-serializable format.

    Args:
        epochs: List of EpochObservations

    Returns:
        List of dictionaries ready for JSON serialization
    """
    result = []

    for epoch in epochs:
        epoch_dict = {"datetime": epoch.datetime.isoformat(), "satellites": []}

        # Process all GNSS systems
        for sat_list, system_code in [
            (epoch.satellites_gps, "G"),
            (epoch.satellites_qzss, "Q"),
            (epoch.satellites_galileo, "E"),
            (epoch.satellites_glonass, "R"),
        ]:
            for sat_obs in sat_list:
                sat_dict = {
                    "system": system_code,
                    "prn": sat_obs.prn,
                    "signals": {},
                    "ambiguities": {},
                }

                # Add signal observations
                for band_name, signal_obs in sat_obs.signals.items():
                    sat_dict["signals"][band_name] = {
                        "pseudorange": signal_obs.pseudorange,
                        "carrier_phase": signal_obs.carrier_phase,
                        "doppler": signal_obs.doppler_,
                        "snr": signal_obs.snr,
                    }

                # Add ambiguity observations
                for comb_name, amb_obs in sat_obs.ambiguities.items():
                    sat_dict["ambiguities"][comb_name] = {
                        "widelane": amb_obs.widelane,
                        "ionofree": amb_obs.ionofree,
                    }

                epoch_dict["satellites"].append(sat_dict)

        result.append(epoch_dict)

    return result


def plot_satellite_observations(epochs, output_dir: Path):
    """
    Plot observations for each satellite.

    Args:
        epochs: List of EpochObservations
        output_dir: Directory to save plots
    """
    # Organize data by satellite
    satellite_data: dict[str, dict] = {}

    for epoch in epochs:
        for sat_list, system_code in [
            (epoch.satellites_gps, "G"),
            (epoch.satellites_qzss, "Q"),
            (epoch.satellites_galileo, "E"),
            (epoch.satellites_glonass, "R"),
        ]:
            for sat_obs in sat_list:
                sat_id = f"{system_code}{sat_obs.prn:02d}"
                if sat_id not in satellite_data:
                    satellite_data[sat_id] = {
                        "pseudorange": {},
                        "carrier_phase": {},
                        "doppler": {},
                        "snr": {},
                        "ambiguities": {},  # key: combination like "L1_L2", value: {"widelane": {...}, "ionofree": {...}}
                    }

                for band_name, signal_obs in sat_obs.signals.items():
                    if band_name not in satellite_data[sat_id]["pseudorange"]:
                        satellite_data[sat_id]["pseudorange"][band_name] = {
                            "times": [],
                            "values": [],
                        }
                        satellite_data[sat_id]["carrier_phase"][band_name] = {
                            "times": [],
                            "values": [],
                        }
                        satellite_data[sat_id]["doppler"][band_name] = {
                            "times": [],
                            "values": [],
                        }
                        satellite_data[sat_id]["snr"][band_name] = {
                            "times": [],
                            "values": [],
                        }

                    satellite_data[sat_id]["pseudorange"][band_name]["times"].append(
                        epoch.datetime
                    )
                    satellite_data[sat_id]["pseudorange"][band_name]["values"].append(
                        signal_obs.pseudorange
                    )
                    satellite_data[sat_id]["carrier_phase"][band_name]["times"].append(
                        epoch.datetime
                    )
                    satellite_data[sat_id]["carrier_phase"][band_name]["values"].append(
                        signal_obs.carrier_phase
                    )
                    satellite_data[sat_id]["doppler"][band_name]["times"].append(
                        epoch.datetime
                    )
                    satellite_data[sat_id]["doppler"][band_name]["values"].append(
                        signal_obs.doppler_
                    )
                    satellite_data[sat_id]["snr"][band_name]["times"].append(
                        epoch.datetime
                    )
                    satellite_data[sat_id]["snr"][band_name]["values"].append(
                        signal_obs.snr
                    )

                # Add ambiguity data for all available combinations
                for comb_name, amb_obs in sat_obs.ambiguities.items():
                    if comb_name not in satellite_data[sat_id]["ambiguities"]:
                        satellite_data[sat_id]["ambiguities"][comb_name] = {
                            "widelane": {"times": [], "values": []},
                            "ionofree": {"times": [], "values": []},
                        }
                    satellite_data[sat_id]["ambiguities"][comb_name]["widelane"][
                        "times"
                    ].append(epoch.datetime)
                    satellite_data[sat_id]["ambiguities"][comb_name]["widelane"][
                        "values"
                    ].append(amb_obs.widelane)
                    satellite_data[sat_id]["ambiguities"][comb_name]["ionofree"][
                        "times"
                    ].append(epoch.datetime)
                    satellite_data[sat_id]["ambiguities"][comb_name]["ionofree"][
                        "values"
                    ].append(amb_obs.ionofree)

    # Create plots for each satellite
    for sat_id, data in satellite_data.items():
        logger.info(f"Plotting satellite {sat_id}")

        # Check if ambiguity data is available and count combinations
        num_ambiguity_combos = len(data["ambiguities"])
        has_ambiguity = num_ambiguity_combos > 0

        # Create a figure with variable subplots
        # 4 basic plots + 2 plots per ambiguity combination
        num_rows = 4 + (2 * num_ambiguity_combos)
        fig, axes = plt.subplots(num_rows, 1, figsize=(12, 3 * num_rows), sharex=True)
        fig.suptitle(f"Satellite {sat_id} Observations", fontsize=16)

        # Handle single subplot case (convert to list)
        if num_rows == 1:
            axes = [axes]

        # Plot pseudorange
        for band_name, band_data in data["pseudorange"].items():
            if band_data["values"]:
                axes[0].plot(
                    band_data["times"],
                    band_data["values"],
                    marker=".",
                    label=f"L{band_name}",
                )
        axes[0].set_ylabel("Pseudorange (m)")
        axes[0].legend()
        axes[0].grid(True)

        # Plot carrier phase
        for band_name, band_data in data["carrier_phase"].items():
            if band_data["values"]:
                axes[1].plot(
                    band_data["times"],
                    band_data["values"],
                    marker=".",
                    label=f"L{band_name}",
                )
        axes[1].set_ylabel("Carrier Phase (cycles)")
        axes[1].legend()
        axes[1].grid(True)

        # Plot doppler
        for band_name, band_data in data["doppler"].items():
            if band_data["values"]:
                axes[2].plot(
                    band_data["times"],
                    band_data["values"],
                    marker=".",
                    label=f"L{band_name}",
                )
        axes[2].set_ylabel("Doppler (Hz)")
        axes[2].legend()
        axes[2].grid(True)

        # Plot SNR
        for band_name, band_data in data["snr"].items():
            if band_data["values"]:
                axes[3].plot(
                    band_data["times"],
                    band_data["values"],
                    marker=".",
                    label=f"L{band_name}",
                )
        axes[3].set_ylabel("SNR (dB-Hz)")
        if not has_ambiguity:
            axes[3].set_xlabel("Time")
        axes[3].legend()
        axes[3].grid(True)

        # Plot ambiguity data for each combination
        if has_ambiguity:
            plot_idx = 4
            colors = ["purple", "orange", "green", "red", "blue", "brown"]
            for comb_idx, (comb_name, comb_data) in enumerate(
                data["ambiguities"].items()
            ):
                color_wl = colors[comb_idx * 2 % len(colors)]
                color_if = colors[(comb_idx * 2 + 1) % len(colors)]

                # Plot widelane ambiguity for this combination
                wl_times = comb_data["widelane"]["times"]
                wl_values = comb_data["widelane"]["values"]
                if wl_values:
                    axes[plot_idx].plot(
                        wl_times,
                        wl_values,
                        marker=".",
                        label=f"{comb_name} WL",
                        color=color_wl,
                    )
                axes[plot_idx].set_ylabel(f"Widelane {comb_name} (cycles)")
                axes[plot_idx].legend()
                axes[plot_idx].grid(True)
                plot_idx += 1

                # Plot ionofree ambiguity for this combination
                if_times = comb_data["ionofree"]["times"]
                if_values = comb_data["ionofree"]["values"]
                if if_values:
                    axes[plot_idx].plot(
                        if_times,
                        if_values,
                        marker=".",
                        label=f"{comb_name} IF",
                        color=color_if,
                    )
                axes[plot_idx].set_ylabel(f"Ionofree {comb_name} (cycles)")
                if plot_idx == num_rows - 1:  # Last plot
                    axes[plot_idx].set_xlabel("Time")
                axes[plot_idx].legend()
                axes[plot_idx].grid(True)
                plot_idx += 1

            # Rotate x-axis labels for better readability
            plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45, ha="right")
        else:
            # Rotate x-axis labels for better readability
            plt.setp(axes[3].xaxis.get_majorticklabels(), rotation=45, ha="right")

        plt.tight_layout()

        # Save the plot
        output_file = output_dir / f"{sat_id}_observations.png"
        plt.savefig(output_file, dpi=150, bbox_inches="tight")
        plt.close()

        logger.info(f"Saved plot to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Process RINEX observation files and generate plots"
    )
    parser.add_argument("rinex_obs", type=str, help="Path to RINEX observation file")
    parser.add_argument(
        "--outdir",
        type=str,
        default="./out/",
        help="Output directory for plots (default: ./out/)",
    )
    parser.add_argument(
        "--json",
        type=str,
        help="Save parsed data to JSON file (specify output file path)",
    )

    args = parser.parse_args()

    # Setup logging
    basicConfig(level=INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # Check if input file exists
    rinex_path = Path(args.rinex_obs)
    if not rinex_path.exists():
        logger.error(f"RINEX file not found: {rinex_path}")
        return 1

    # Create output directory if it doesn't exist
    output_dir = Path(args.outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Parse RINEX file
    logger.info(f"Parsing RINEX file: {rinex_path}")
    epochs: list[EpochObservations] = parse_rinex_observation_file(str(rinex_path))
    logger.info(f"Parsed {len(epochs)} epochs")

    # Save to JSON if requested
    if args.json:
        json_output_path = Path(args.json)
        save_gnss_observations_to_json(epochs, json_output_path)
        logger.info(f"Saved parsed data to JSON: {json_output_path}")

    # Generate plots
    logger.info("Generating plots...")
    plot_satellite_observations(epochs, output_dir)

    logger.info("Done!")
    return 0


if __name__ == "__main__":
    exit(main())
