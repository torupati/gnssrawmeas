import argparse
from bisect import bisect_left  # Find insertion index in a sorted list (binary search)
from datetime import datetime
import json
from pathlib import Path
from logging import getLogger, basicConfig, INFO

import matplotlib.pyplot as plt

from app.gnss.satellite_signals import (
    EpochObservations,
    PairedObservation,
    SatelliteObservation,
    parse_rinex_observation_file,
)

logger = getLogger(__name__)


def _build_satellite_signal_map(epoch: EpochObservations) -> dict[str, set[str]]:
    sat_signals: dict[str, set[str]] = {}
    for sat_id, sat_obs in epoch.iter_satellites():
        sat_signals[sat_id] = set(sat_obs.signals.keys())
    return sat_signals


def _build_satellite_obs_map(
    epoch: EpochObservations,
) -> dict[str, SatelliteObservation]:
    sat_map: dict[str, SatelliteObservation] = {}
    for sat_id, sat_obs in epoch.iter_satellites():
        sat_map[sat_id] = sat_obs
    return sat_map


def _load_satpair_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return [
            {"sat1": item[0], "sat2": item[1], "combinations": None} for item in data
        ]

    if not isinstance(data, dict):
        raise ValueError("satpair JSON must be a list or an object")

    if "combined" in data:
        combined = data.get("combined")
        if not isinstance(combined, list):
            raise ValueError("combined must be a list in satpair JSON")
        combined_entries: list[dict] = []
        for item in combined:
            if not isinstance(item, dict):
                raise ValueError("combined items must be objects")
            satellites = item.get("satellites")
            bands = item.get("bands")
            if not isinstance(satellites, list) or len(satellites) != 2:
                raise ValueError("satellites must be a list of length 2")
            if bands is not None and not isinstance(bands, list):
                raise ValueError("bands must be a list")
            combined_entries.append(
                {
                    "sat1": str(satellites[0]),
                    "sat2": str(satellites[1]),
                    "combinations": [str(item) for item in bands] if bands else None,
                }
            )
        return combined_entries

    sat_pairs_raw = data.get("sat_pairs")
    if not isinstance(sat_pairs_raw, list):
        raise ValueError("sat_pairs must be a list in satpair JSON")

    default_combinations = data.get("combinations")
    if default_combinations is not None and not isinstance(default_combinations, list):
        raise ValueError("combinations must be a list in satpair JSON")

    entries: list[dict] = []
    for item in sat_pairs_raw:
        if isinstance(item, dict):
            pair = item.get("pair")
            if not isinstance(pair, list) or len(pair) != 2:
                raise ValueError("pair must be a list of length 2 in satpair JSON")
            combinations = item.get("combinations", default_combinations)
        else:
            pair = item
            combinations = default_combinations

        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError("sat_pairs items must be [sat1, sat2]")
        if combinations is not None and not isinstance(combinations, list):
            raise ValueError("combinations must be a list in satpair JSON")

        entries.append(
            {
                "sat1": str(pair[0]),
                "sat2": str(pair[1]),
                "combinations": (
                    [str(item) for item in combinations]
                    if combinations is not None
                    else None
                ),
            }
        )

    return entries


def _compute_double_difference_for_pair(
    observation: EpochObservations,
    ref_observation: EpochObservations,
    sat1: str,
    sat2: str,
    combination: str,
) -> dict:
    obs_map = _build_satellite_obs_map(observation)
    ref_map = _build_satellite_obs_map(ref_observation)

    obs_sat1 = obs_map.get(sat1)
    obs_sat2 = obs_map.get(sat2)
    ref_sat1 = ref_map.get(sat1)
    ref_sat2 = ref_map.get(sat2)

    if not (obs_sat1 and obs_sat2 and ref_sat1 and ref_sat2):
        return {
            "sat1": sat1,
            "sat2": sat2,
            "combination": combination,
            "widelane": None,
            "ionofree": None,
        }

    obs_amb1 = obs_sat1.ambiguities.get(combination)
    obs_amb2 = obs_sat2.ambiguities.get(combination)
    ref_amb1 = ref_sat1.ambiguities.get(combination)
    ref_amb2 = ref_sat2.ambiguities.get(combination)

    if not (obs_amb1 and obs_amb2 and ref_amb1 and ref_amb2):
        return {
            "sat1": sat1,
            "sat2": sat2,
            "combination": combination,
            "widelane": None,
            "ionofree": None,
        }

    widelane_dd = (obs_amb1.widelane - obs_amb2.widelane) - (
        ref_amb1.widelane - ref_amb2.widelane
    )
    ionofree_dd = (obs_amb1.ionofree - obs_amb2.ionofree) - (
        ref_amb1.ionofree - ref_amb2.ionofree
    )

    return {
        "sat1": sat1,
        "sat2": sat2,
        "combination": combination,
        "widelane": widelane_dd,
        "ionofree": ionofree_dd,
    }


def _init_satellite_data_entry() -> dict:
    return {
        "pseudorange": {},
        "carrier_phase": {},
        "doppler": {},
        "snr": {},
        "ambiguities": {},
    }


def _collect_satellite_data(epochs: list[EpochObservations]) -> dict[str, dict]:
    satellite_data: dict[str, dict] = {}

    for epoch in epochs:
        for sat_id, sat_obs in epoch.iter_satellites():
            if sat_id not in satellite_data:
                satellite_data[sat_id] = _init_satellite_data_entry()

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
                satellite_data[sat_id]["snr"][band_name]["times"].append(epoch.datetime)
                satellite_data[sat_id]["snr"][band_name]["values"].append(
                    signal_obs.snr
                )

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

    return satellite_data


def plot_paired_satellite_observations(
    paired: list[PairedObservation],
    output_dir: Path,
    plot_mode: int = 1,
):
    """Plot observations for paired satellite data.

    Args:
        paired (list[PairedObservation]): time synchronized observation epochs
        output_dir (Path): output directory for plots
        plot_mode (int, optional): Plot mode selection. Defaults to 1.
    """
    input_epochs = [pair.observation for pair in paired]
    ref_epochs = [pair.ref_observation for pair in paired]
    input_data = _collect_satellite_data(input_epochs)
    ref_data = _collect_satellite_data(ref_epochs)

    if len(input_data) < 2:
        logger.warning("Number of satellites in input observations less than 2")
        return
    if len(ref_data) == 0:
        logger.warning("No satellite data found in reference observations")
        return
    common_sats = sorted(set(input_data.keys()) & set(ref_data.keys()))
    start_time = input_epochs[0].datetime
    end_time = input_epochs[-1].datetime

    for sat_id in common_sats:
        logger.info(f"Plotting paired satellite {sat_id}")

        data_left = input_data[sat_id]
        data_right = ref_data[sat_id]

        all_times = []
        for data in (data_left, data_right):
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

        #        common_start = min(all_times) if all_times else None
        #        common_end = max(all_times) if all_times else None

        num_ambiguity_combos = len(
            set(data_left["ambiguities"].keys()) | set(data_right["ambiguities"].keys())
        )
        has_ambiguity = num_ambiguity_combos > 0

        show_basic = plot_mode in {1, 4}
        show_snr = plot_mode in {1, 2, 3, 4}
        show_widelane = plot_mode in {1, 2, 3}
        show_ionofree = plot_mode in {1, 3}

        if plot_mode == 4:
            has_ambiguity = False

        num_rows = 0
        if show_basic:
            num_rows += 3
        if show_snr:
            num_rows += 1
        if has_ambiguity:
            if show_widelane:
                num_rows += num_ambiguity_combos
            if show_ionofree:
                num_rows += num_ambiguity_combos

        fig, axes = plt.subplots(
            num_rows,
            2,
            figsize=(18, 3 * num_rows),
            sharex="col",
        )
        fig.suptitle(f"Satellite {sat_id} Observations (Input | Reference)")

        if num_rows == 1:
            axes = [axes]

        plot_idx = 0

        def plot_band_row(ax, data, key, ylabel):
            for band_name, band_data in data[key].items():
                if band_data["values"]:
                    ax.plot(
                        band_data["times"],
                        band_data["values"],
                        marker=".",
                        linestyle="None",
                        label=f"{band_name}",
                    )
            ax.set_ylabel(ylabel)
            ax.legend()
            ax.grid(True)

        if show_basic:
            plot_band_row(
                axes[plot_idx][0], data_left, "pseudorange", "Pseudorange (m)"
            )
            plot_band_row(
                axes[plot_idx][1], data_right, "pseudorange", "Pseudorange (m)"
            )
            plot_idx += 1

            plot_band_row(
                axes[plot_idx][0],
                data_left,
                "carrier_phase",
                "Carrier Phase (cycles)",
            )
            plot_band_row(
                axes[plot_idx][1],
                data_right,
                "carrier_phase",
                "Carrier Phase (cycles)",
            )
            plot_idx += 1

            plot_band_row(axes[plot_idx][0], data_left, "doppler", "Doppler (Hz)")
            plot_band_row(axes[plot_idx][1], data_right, "doppler", "Doppler (Hz)")
            plot_idx += 1

        if show_snr:
            plot_band_row(axes[plot_idx][0], data_left, "snr", "SNR (dB-Hz)")
            plot_band_row(axes[plot_idx][1], data_right, "snr", "SNR (dB-Hz)")
            axes[plot_idx][0].set_ylim(30, 60)
            axes[plot_idx][1].set_ylim(30, 60)
            plot_idx += 1

        if has_ambiguity:
            colors = ["purple", "orange", "green", "red", "blue", "brown"]
            all_combos = sorted(
                set(data_left["ambiguities"].keys())
                | set(data_right["ambiguities"].keys())
            )
            for comb_idx, comb_name in enumerate(all_combos):
                color_wl = colors[comb_idx * 2 % len(colors)]
                color_if = colors[(comb_idx * 2 + 1) % len(colors)]

                if show_widelane:
                    for ax, data in zip(axes[plot_idx], (data_left, data_right)):
                        comb_data = data["ambiguities"].get(comb_name)
                        if comb_data:
                            wl_times = comb_data["widelane"]["times"]
                            wl_values = comb_data["widelane"]["values"]
                            if wl_values:
                                ax.plot(
                                    wl_times,
                                    wl_values,
                                    marker=".",
                                    linestyle="None",
                                    label=f"{comb_name} WL",
                                    color=color_wl,
                                )
                        ax.set_ylabel(f"Widelane {comb_name} (cycles)")
                        ax.legend()
                        ax.grid(True)
                    plot_idx += 1

                if show_ionofree:
                    for ax, data in zip(axes[plot_idx], (data_left, data_right)):
                        comb_data = data["ambiguities"].get(comb_name)
                        if comb_data:
                            if_times = comb_data["ionofree"]["times"]
                            if_values = comb_data["ionofree"]["values"]
                            if if_values:
                                ax.plot(
                                    if_times,
                                    if_values,
                                    marker=".",
                                    linestyle="None",
                                    label=f"{comb_name} IF",
                                    color=color_if,
                                )
                        ax.set_ylabel(f"Ionofree {comb_name} (cycles)")
                        ax.legend()
                        ax.grid(True)
                    plot_idx += 1

        plt.setp(axes[-1][0].xaxis.get_majorticklabels(), rotation=45, ha="right")
        plt.setp(axes[-1][1].xaxis.get_majorticklabels(), rotation=45, ha="right")

        plt.tight_layout()

        for row_axes in axes:
            row_axes[0].set_xlim(start_time, end_time)
            row_axes[1].set_xlim(start_time, end_time)

        axes[-1][0].set_xlabel("Time")
        axes[-1][1].set_xlabel("Time")

        output_file = output_dir / f"{sat_id}_paired_observations.png"
        plt.savefig(output_file, dpi=150, bbox_inches="tight")
        plt.close()

        logger.info(f"Saved plot to {output_file}")


def _collect_combined_observation_series(
    paired: list[PairedObservation],
) -> dict[tuple[str, str, str], dict]:
    combined_series: dict[tuple[str, str, str], dict] = {}
    for pair in paired:
        if not pair.combined_observations:
            continue
        for entry in pair.combined_observations:
            sat1 = entry.get("sat1")
            sat2 = entry.get("sat2")
            comb = entry.get("combination")
            if not (sat1 and sat2 and comb):
                continue

            key = (sat1, sat2, comb)
            if key not in combined_series:
                combined_series[key] = {
                    "widelane": {"times": [], "values": []},
                    "ionofree": {"times": [], "values": []},
                }

            widelane = entry.get("widelane")
            ionofree = entry.get("ionofree")

            if widelane is not None:
                combined_series[key]["widelane"]["times"].append(pair.datetime)
                combined_series[key]["widelane"]["values"].append(widelane)

            if ionofree is not None:
                combined_series[key]["ionofree"]["times"].append(pair.datetime)
                combined_series[key]["ionofree"]["values"].append(ionofree)

    return combined_series


def plot_combined_observations(
    paired: list[PairedObservation],
    output_dir: Path,
    plot_mode: int = 1,
):
    if not paired:
        logger.warning("No paired observations available for combined plots")
        return

    combined_series = _collect_combined_observation_series(paired)
    if not combined_series:
        logger.warning("No combined observations found for plotting")
        return

    show_widelane = plot_mode in {1, 2, 3}
    show_ionofree = plot_mode in {1, 3}

    if not (show_widelane or show_ionofree):
        logger.info("Plot mode excludes combined observation plots")
        return

    start_time = min(pair.datetime for pair in paired)
    end_time = max(pair.datetime for pair in paired)

    for (sat1, sat2, comb), data in combined_series.items():
        num_rows = 0
        if show_widelane:
            num_rows += 1
        if show_ionofree:
            num_rows += 1

        fig, axes = plt.subplots(
            num_rows,
            1,
            figsize=(12, 3 * num_rows),
            sharex=True,
        )
        fig.suptitle(f"Combined {sat1}-{sat2} {comb} (Double Difference)")

        if num_rows == 1:
            axes = [axes]

        plot_idx = 0

        if show_widelane:
            ax = axes[plot_idx]
            wl_times = data["widelane"]["times"]
            wl_values = data["widelane"]["values"]
            if wl_values:
                ax.plot(wl_times, wl_values, marker=".", linestyle="None")
            ax.set_ylabel(f"Widelane {comb} (cycles)")
            ax.grid(True)
            plot_idx += 1

        if show_ionofree:
            ax = axes[plot_idx]
            if_times = data["ionofree"]["times"]
            if_values = data["ionofree"]["values"]
            if if_values:
                ax.plot(if_times, if_values, marker=".", linestyle="None")
            ax.set_ylabel(f"Ionofree {comb} (cycles)")
            ax.grid(True)
            plot_idx += 1

        plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45, ha="right")
        plt.tight_layout()

        axes[-1].set_xlim(start_time, end_time)

        output_file = output_dir / f"{sat1}_{sat2}_{comb}_combined.png"
        plt.savefig(output_file, dpi=150, bbox_inches="tight")
        plt.close()

        logger.info(f"Saved combined plot to {output_file}")


def _find_closest_epoch(
    ref_epochs: list[EpochObservations],
    ref_times: list[datetime],
    target_time: datetime,
) -> EpochObservations:
    if not ref_epochs:
        raise ValueError("Reference epochs are empty")
    idx = bisect_left(ref_times, target_time)
    if idx == 0:
        return ref_epochs[0]
    if idx >= len(ref_times):
        return ref_epochs[-1]
    before = ref_epochs[idx - 1]
    after = ref_epochs[idx]
    if abs((target_time - before.datetime).total_seconds()) <= abs(
        (after.datetime - target_time).total_seconds()
    ):
        return before
    return after


def pair_observations(
    epochs: list[EpochObservations],
    ref_epochs: list[EpochObservations],
) -> list[PairedObservation]:
    ref_times = [epoch.datetime for epoch in ref_epochs]
    paired: list[PairedObservation] = []
    for epoch in epochs:
        ref_epoch = _find_closest_epoch(ref_epochs, ref_times, epoch.datetime)
        paired.append(
            PairedObservation(
                epoch=epoch.datetime.isoformat(),
                datetime=epoch.datetime,
                observation=epoch,
                ref_observation=ref_epoch,
                combined_observations=[],
            )
        )
    return paired


def _update_combined_observations(
    paired_epochs: list[PairedObservation],
    sat_pairs: list[dict],
):
    for pair in paired_epochs:
        combined = []
        obs_map = _build_satellite_obs_map(pair.observation)
        ref_map = _build_satellite_obs_map(pair.ref_observation)
        for entry in sat_pairs:
            sat1 = entry["sat1"]
            sat2 = entry["sat2"]
            combinations = entry.get("combinations")

            obs_sat1 = obs_map.get(sat1)
            obs_sat2 = obs_map.get(sat2)
            ref_sat1 = ref_map.get(sat1)
            ref_sat2 = ref_map.get(sat2)

            if not (obs_sat1 and obs_sat2 and ref_sat1 and ref_sat2):
                logger.warning(
                    f"Satellites {sat1} or {sat2} not found in observations at {pair.datetime}"
                )
                continue

            obs_keys = set(obs_sat1.ambiguities.keys()) & set(
                obs_sat2.ambiguities.keys()
            )
            ref_keys = set(ref_sat1.ambiguities.keys()) & set(
                ref_sat2.ambiguities.keys()
            )
            common_keys = sorted(obs_keys & ref_keys)

            if combinations is not None:
                common_keys = [key for key in common_keys if key in combinations]

            if not common_keys:
                logger.warning(
                    f"No common ambiguity combinations for satellites {sat1} and {sat2} at {pair.datetime}"
                )
                continue

            for comb in common_keys:
                combined.append(
                    _compute_double_difference_for_pair(
                        pair.observation, pair.ref_observation, sat1, sat2, comb
                    )
                )

        pair.combined_observations = combined


def _paired_observations_to_json(paired_epochs: list[PairedObservation]) -> list[dict]:
    output = []
    for pair in paired_epochs:
        output.append(
            {
                "epoch": pair.epoch,
                "datetime": pair.datetime.isoformat(),
                "ref_datetime": pair.ref_observation.datetime.isoformat(),
                "age_seconds": pair.age_seconds,
                "combined_observations": pair.combined_observations,
            }
        )
    return output


def _print_common_non_l1_signals(paired_epochs: list[PairedObservation]):
    for pair in paired_epochs:
        obs_map = _build_satellite_signal_map(pair.observation)
        ref_map = _build_satellite_signal_map(pair.ref_observation)
        common_sats = sorted(set(obs_map.keys()) & set(ref_map.keys()))

        print(
            f"{pair.time_str} | ref {pair.ref_observation.datetime.strftime('%Y-%m-%d %H:%M:%S')} | dt={pair.age_seconds:+.3f}s"
        )
        any_found = False
        for sat_id in common_sats:
            common_signals = (obs_map[sat_id] & ref_map[sat_id]) - {"L1"}
            if not common_signals:
                continue
            any_found = True
            signals_str = ", ".join(sorted(common_signals))
            print(f"  {sat_id}: {signals_str}")
        if not any_found:
            print("  (no common non-L1 signals)")


def main():
    parser = argparse.ArgumentParser(
        description="Pair RINEX observation files and list common non-L1 signals"
    )
    parser.add_argument("rinex_obs", type=str, help="Path to input RINEX file")
    parser.add_argument("rinex_ref", type=str, help="Path to reference RINEX file")
    parser.add_argument(
        "--outdir",
        type=str,
        default="./out/",
        help="Output directory for plots (default: ./out/)",
    )
    parser.add_argument(
        "--plot-mode",
        type=int,
        choices=[1, 2, 3, 4],
        default=1,
        help=(
            "Plot data selection: 1=all, 2=SNR+widelane only, "
            "3=SNR+widelane+ionofree only, 4=PR+CP+Doppler+SNR only"
        ),
    )
    parser.add_argument(
        "--skip-plot",
        action="store_true",
        help="Skip generating plots",
    )
    parser.add_argument(
        "--satpair",
        type=str,
        required=True,
        help="Path to satpair JSON file (e.g., sat_pair.json)",
    )
    parser.add_argument(
        "--paired-json",
        type=str,
        default="./paired_observations.json",
        help="Output JSON file for paired observations (default: ./paired_observations.json)",
    )
    parser.add_argument(
        "--signal-code-map",
        type=str,
        default=str(Path(__file__).parent / ".signal_code_map.json"),
        help=(
            "Path to JSON file that defines signal_code_map "
            "(default: .signal_code_map.json)"
        ),
    )

    args = parser.parse_args()

    basicConfig(level=INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    rinex_path = Path(args.rinex_obs)
    ref_path = Path(args.rinex_ref)
    if not rinex_path.exists():
        logger.error(f"RINEX file not found: {rinex_path}")
        return 1
    if not ref_path.exists():
        logger.error(f"Reference RINEX file not found: {ref_path}")
        return 1

    signal_code_map_path = Path(args.signal_code_map)
    if not signal_code_map_path.exists():
        logger.error(f"Signal code map file not found: {signal_code_map_path}")
        return 1
    try:
        with signal_code_map_path.open("r", encoding="utf-8") as f:
            signal_code_map = json.load(f)
    except json.JSONDecodeError as exc:
        logger.error(
            f"Invalid JSON in signal code map file: {signal_code_map_path} ({exc})"
        )
        return 1

    logger.info(f"... input RINEX file: {rinex_path}")
    epochs: list[EpochObservations] = parse_rinex_observation_file(
        str(rinex_path), signal_code_map
    )
    logger.info(
        f"... parsed {len(epochs)} epochs. {epochs[0].datetime if epochs else 'N/A'} to {epochs[-1].datetime if epochs else 'N/A'}"
    )

    logger.info(f"... reference RINEX file: {ref_path}")
    ref_epochs: list[EpochObservations] = parse_rinex_observation_file(
        str(ref_path), signal_code_map
    )
    logger.info(
        f"... parsed {len(ref_epochs)} epochs. {ref_epochs[0].datetime if ref_epochs else 'N/A'} to {ref_epochs[-1].datetime if ref_epochs else 'N/A'}"
    )

    if not epochs or not ref_epochs:
        logger.error("Input or reference epochs are empty")
        return 1

    logger.info("... pairing observations...")
    paired = pair_observations(epochs, ref_epochs)
    satpair_path = Path(args.satpair)
    if not satpair_path.exists():
        logger.error(f"satpair JSON file not found: {satpair_path}")
        return 1
    try:
        sat_pairs = _load_satpair_json(satpair_path)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.error(f"Invalid satpair JSON: {exc}")
        return 1
    _update_combined_observations(paired, sat_pairs)
    paired_json_path = Path(args.paired_json)
    paired_json_path.parent.mkdir(parents=True, exist_ok=True)
    with paired_json_path.open("w", encoding="utf-8") as f:
        json.dump(_paired_observations_to_json(paired), f, indent=2)
    logger.info(f"Saved paired observations to JSON: {paired_json_path}")
    _print_common_non_l1_signals(paired)

    output_dir = Path(args.outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    if args.skip_plot:
        logger.info("Skipping plot generation (--skip-plot)")
    else:
        logger.info("Generating paired plots...")
        plot_paired_satellite_observations(paired, output_dir, plot_mode=args.plot_mode)
        logger.info("Generating combined observation plots...")
        plot_combined_observations(paired, output_dir, plot_mode=args.plot_mode)
    return 0


if __name__ == "__main__":
    exit(main())
