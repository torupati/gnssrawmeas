import logging
from pathlib import Path

import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


def plot_satellite_observations(epochs, output_dir: Path, plot_mode: int = 1):
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
            (epoch.satellites_qzss, "J"),
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

        # Determine common time range across all plots for this satellite
        all_times = []
        for band_data in data["pseudorange"].values():
            all_times.extend(band_data["times"])
        for band_data in data["carrier_phase"].values():
            all_times.extend(band_data["times"])
        for band_data in data["doppler"].values():
            all_times.extend(band_data["times"])
        for band_data in data["snr"].values():
            all_times.extend(band_data["times"])
        for comb_data in data["ambiguities"].values():
            all_times.extend(comb_data["widelane"]["times"])
            all_times.extend(comb_data["ionofree"]["times"])
        if all_times:
            common_start = min(all_times)
            common_end = max(all_times)
        else:
            common_start = None
            common_end = None

        # Check if ambiguity data is available and count combinations
        num_ambiguity_combos = len(data["ambiguities"])
        has_ambiguity = num_ambiguity_combos > 0

        show_basic = plot_mode in {1, 4}
        show_snr = plot_mode in {1, 2, 3, 4}
        show_widelane = plot_mode in {1, 2, 3}
        show_ionofree = plot_mode in {1, 3}

        if plot_mode == 4:
            has_ambiguity = False

        # Create a figure with variable subplots
        num_rows = 0
        if show_basic:
            num_rows += 3  # pseudorange, carrier phase, doppler
        if show_snr:
            num_rows += 1
        if has_ambiguity:
            if show_widelane:
                num_rows += num_ambiguity_combos
            if show_ionofree:
                num_rows += num_ambiguity_combos
        fig, axes = plt.subplots(num_rows, 1, figsize=(12, 3 * num_rows), sharex=True)
        fig.suptitle(f"Satellite {sat_id} Observations", fontsize=16)

        # Handle single subplot case (convert to list)
        if num_rows == 1:
            axes = [axes]

        plot_idx = 0

        # Plot pseudorange
        if show_basic:
            for band_name, band_data in data["pseudorange"].items():
                if band_data["values"]:
                    axes[plot_idx].plot(
                        band_data["times"],
                        band_data["values"],
                        marker=".",
                        linestyle="None",
                        label=band_name,
                    )
            axes[plot_idx].set_ylabel("Pseudorange (m)")
            axes[plot_idx].legend()
            axes[plot_idx].grid(True)
            plot_idx += 1

            # Plot carrier phase
            for band_name, band_data in data["carrier_phase"].items():
                if band_data["values"]:
                    axes[plot_idx].plot(
                        band_data["times"],
                        band_data["values"],
                        marker=".",
                        linestyle="None",
                        label=band_name,
                    )
            axes[plot_idx].set_ylabel("Carrier Phase (cycles)")
            axes[plot_idx].legend()
            axes[plot_idx].grid(True)
            plot_idx += 1

            # Plot doppler
            for band_name, band_data in data["doppler"].items():
                if band_data["values"]:
                    axes[plot_idx].plot(
                        band_data["times"],
                        band_data["values"],
                        marker=".",
                        linestyle="None",
                        label=band_name,
                    )
            axes[plot_idx].set_ylabel("Doppler (Hz)")
            axes[plot_idx].legend()
            axes[plot_idx].grid(True)
            plot_idx += 1

        # Plot SNR
        if show_snr:
            for band_name, band_data in data["snr"].items():
                if band_data["values"]:
                    axes[plot_idx].plot(
                        band_data["times"],
                        band_data["values"],
                        marker=".",
                        linestyle="None",
                        label=band_name,
                    )
            axes[plot_idx].set_ylabel("SNR (dB-Hz)")
            axes[plot_idx].legend()
            axes[plot_idx].grid(True)
            plot_idx += 1

        # Plot ambiguity data for each combination
        if has_ambiguity:
            colors = ["purple", "orange", "green", "red", "blue", "brown"]
            for comb_idx, (comb_name, comb_data) in enumerate(
                data["ambiguities"].items()
            ):
                color_wl = colors[comb_idx * 2 % len(colors)]
                color_if = colors[(comb_idx * 2 + 1) % len(colors)]

                # Plot widelane ambiguity for this combination
                if show_widelane:
                    wl_times = comb_data["widelane"]["times"]
                    wl_values = comb_data["widelane"]["values"]
                    if wl_values:
                        axes[plot_idx].plot(
                            wl_times,
                            wl_values,
                            marker=".",
                            linestyle="None",
                            label=f"{comb_name} WL",
                            color=color_wl,
                        )
                    axes[plot_idx].set_ylabel(f"Widelane {comb_name} (cycles)")
                    axes[plot_idx].legend()
                    axes[plot_idx].grid(True)
                    plot_idx += 1

                # Plot ionofree ambiguity for this combination
                if show_ionofree:
                    if_times = comb_data["ionofree"]["times"]
                    if_values = comb_data["ionofree"]["values"]
                    if if_values:
                        axes[plot_idx].plot(
                            if_times,
                            if_values,
                            marker=".",
                            linestyle="None",
                            label=f"{comb_name} IF",
                            color=color_if,
                        )
                    axes[plot_idx].set_ylabel(f"Ionofree {comb_name} (cycles)")
                    axes[plot_idx].legend()
                    axes[plot_idx].grid(True)
                    plot_idx += 1

            # Rotate x-axis labels for better readability
            plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45, ha="right")
        else:
            # Rotate x-axis labels for better readability
            plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45, ha="right")

        plt.tight_layout()

        if common_start is not None and common_end is not None:
            for ax in axes:
                ax.set_xlim(common_start, common_end)

        if len(axes) > 0:
            axes[-1].set_xlabel("Time")

        # Save the plot
        output_file = output_dir / f"{sat_id}_observations.png"
        plt.savefig(output_file, dpi=150, bbox_inches="tight")
        plt.close()

        logger.info(f"Saved plot to {output_file}")
