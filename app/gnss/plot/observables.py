import logging
from pathlib import Path

import matplotlib.pyplot as plt
from georinex import rinexobs


from app.gnss.satellite_signals import get_available_signal_code
from app.gnss.constants import wlen_L1, wlen_L2, wlen_L5, CLIGHT, L1_FREQ, L2_FREQ
from app.gnss.ambiguity import (
    get_widelane_ambiguity,
    get_narrowlane_ambiguity,
)

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
                        label=f"L{band_name}",
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
                        label=f"L{band_name}",
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
                        label=f"L{band_name}",
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
                        label=f"L{band_name}",
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


# --------


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
    amb_wl = get_widelane_ambiguity(
        rnxobs,
        satname,
        f"C1{l1_signal_code}",
        f"L1{l1_signal_code}",
        f"C2{l2_signal_code}",
        f"L2{l2_signal_code}",
    )
    # Use the time-average of the wide-lane ambiguity in downstream computation
    amb_wl_mean = float(amb_wl.mean().values)

    # Iono-free combination
    amb_n1 = get_narrowlane_ambiguity(
        rnxobs,
        satname,
        amb_wl_mean,
        f"C1{l1_signal_code}",
        f"L1{l1_signal_code}",
        f"C2{l2_signal_code}",
        f"L2{l2_signal_code}",
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
