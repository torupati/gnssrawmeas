#!/usr/bin/env python3
"""
Compare time epochs between two GNSS observation JSON files.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import numpy as np
import matplotlib.pyplot as plt

from app.gnss.constants import iono_wlen


def plot_obs(
    data2recvs: list,
    satname1: str,
    satname2: str,
):
    """Plot differences between two receivers and two satellites.

    Args:
        satname1 (str): Satellite name 1
        satname2 (str): Satellite name 2

    Returns:
        _type_: _description_
    """
    _tmp_data: dict[str, list[Union[datetime, float]]] = {
        "time": [],
        "amb_wl_diff": [],
        "amb_iono_diff": [],
        "S1_sat1_rec1": [],
        "S1_sat1_rec2": [],
        "S1_sat2_rec1": [],
        "S1_sat2_rec2": [],
    }
    for data in data2recvs:
        # print("analysing time:",data)
        if satname1 not in data.get("ambiguity_differences", {}).keys():
            continue
        if satname2 not in data.get("ambiguity_differences", {}).keys():
            continue
        amb_wl_1 = data["ambiguity_differences"][satname1].get("widelane_L1L2", None)
        amb_wl_2 = data["ambiguity_differences"][satname2].get("widelane_L1L2", None)
        amb_iono_1 = data["ambiguity_differences"][satname1].get(
            "ionospheric_L1L2", None
        )
        amb_iono_2 = data["ambiguity_differences"][satname2].get(
            "ionospheric_L1L2", None
        )
        if amb_wl_1 is None or amb_wl_2 is None:
            continue
        if amb_iono_1 is None or amb_iono_2 is None:
            continue
        amb_wl_sat12_rec12 = amb_wl_2 - amb_wl_1
        amb_iono_sat12_rec12 = amb_iono_2 - amb_iono_1
        _tmp_data["time"].append(data["time"])
        _tmp_data["amb_wl_diff"].append(amb_wl_sat12_rec12)
        _tmp_data["amb_iono_diff"].append(amb_iono_sat12_rec12)
        _tmp_data["S1_sat1_rec1"].append(
            data["ambiguity_differences"][satname1].get("S1_rec1", None)
        )
        _tmp_data["S1_sat1_rec2"].append(
            data["ambiguity_differences"][satname1].get("S1_rec2", None)
        )
        _tmp_data["S1_sat2_rec1"].append(
            data["ambiguity_differences"][satname2].get("S1_rec1", None)
        )
        _tmp_data["S1_sat2_rec2"].append(
            data["ambiguity_differences"][satname2].get("S1_rec2", None)
        )
        # print(f"{data['time']}  WL DD {satname1}-{satname2}: {amb_wl_sat12_rec12:+.6f} cycle, IONO DD {satname1}-{satname2}: {amb_iono_sat12_rec12:+.6f} m")
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    axes[0].set_title(
        rf"Wide-lane Ambiguity DD {satname1}-{satname2} $N_{{L1}} - N_{{L2}}$"
    )
    axes[0].plot(
        _tmp_data["time"],
        _tmp_data["amb_wl_diff"],
        ".",
        label=f"Sat {satname1} - Sat {satname2} Rec1 - Rec2",
    )
    axes[0].axhline(
        np.mean(_tmp_data["amb_wl_diff"]), color="gray", linestyle="--", label="Mean"
    )
    axes[0].axhline(
        np.round(np.mean(_tmp_data["amb_wl_diff"])),
        color="gray",
        linestyle="--",
        label="Nearest Integer",
    )
    axes[0].set_ylabel(r"$\Delta B_{wl}$ [cycle]")

    axes[1].set_title(rf"Iono-free Ambiguity DD {satname1}-{satname2} $N_{{L1}}$")
    axes[1].plot(
        _tmp_data["time"],
        np.array(_tmp_data["amb_iono_diff"]) / iono_wlen,
        ".",
        label=f"Sat {satname1} - Sat {satname2} Rec1 - Rec2",
    )
    axes[1].axhline(
        np.mean(np.array(_tmp_data["amb_iono_diff"])) / iono_wlen,
        color="gray",
        linestyle="--",
        label="Mean",
    )
    axes[1].set_ylabel(r"$\Delta B_{iono}$ [cycle]")

    axes[2].set_title("Signal Strength")
    for key in ["S1_sat1_rec1", "S1_sat1_rec2", "S1_sat2_rec1", "S1_sat2_rec2"]:
        axes[2].plot(
            _tmp_data["time"],
            _tmp_data[key],
            ".",
            label=key,
        )
        axes[2].set_ylabel("C/N0 [dB-Hz]")  #
    axes[2].legend(loc="upper right", fontsize="small")
    for ax in axes:
        ax.grid(True)
    axes[2].set_xlabel("GPST")
    axes[2].set_xlim(_tmp_data["time"][0], _tmp_data["time"][-1])
    return fig, axes


def load_json_file(filepath: str) -> dict:
    """Load JSON file and return the data."""

    def parse_time(time_str: str) -> datetime:
        """Parse ISO format time string to datetime."""
        return datetime.fromisoformat(time_str.replace("Z", "+00:00"))

    with open(filepath, "r") as f:
        data = json.load(f)
        for entry in data["data"]:
            entry["time"] = parse_time(entry["time"])
        return data


def find_closest_time_index(
    target_time: datetime, time_list: list[dict]
) -> tuple[int, datetime]:
    """
    Find the closest time index in time_list to target_time.

    Args:
        target_time: Target datetime to match
        time_list: List of data dictionaries containing 'time' field

    Returns:
        Tuple of (index, datetime) for the closest match
    """
    min_diff: Optional[float] = None
    closest_idx: int = 0
    closest_time: datetime = time_list[0]["time"]

    for idx, entry in enumerate(time_list):
        entry_time = entry["time"]
        diff = abs((target_time - entry_time).total_seconds())

        if min_diff is None or diff < min_diff:
            min_diff = diff
            closest_idx = idx
            closest_time = entry_time

    return closest_idx, closest_time


def compare_ambiguities(entry1: dict, entry2: dict) -> dict:
    """
    Compare ambiguities for common satellites between two observation entries.

    Args:
        entry1: First observation entry
        entry2: Second observation entry

    Returns:
        Dictionary with common satellites and their ambiguity differences
    """
    ambig1 = entry1.get("ambiguities", {})
    ambig2 = entry2.get("ambiguities", {})

    # Find common satellites
    sats1 = set(ambig1.keys())
    sats2 = set(ambig2.keys())
    common_sats = sorted(sats1 & sats2)

    differences: dict[str, dict[str, Optional[float]]] = {}

    for sat in common_sats:
        sat_ambig1 = ambig1[sat]
        sat_ambig2 = ambig2[sat]

        differences[sat] = {}

        for key in ["widelane_L1L2", "ionospheric_L1L2"]:
            if key in sat_ambig2:
                val1 = sat_ambig1[key]
                val2 = sat_ambig2[key]

                # Calculate difference only if both values are not None
                if val1 is not None and val2 is not None:
                    differences[sat][key] = val2 - val1
                else:
                    differences[sat][key] = None
        for key in ["S1", "S2"]:
            if key in sat_ambig2:
                val1 = sat_ambig1[key]
                val2 = sat_ambig2[key]

                # Calculate difference only if both values are not None
                if val1 is not None and val2 is not None:
                    differences[sat]["S1_rec1"] = val1
                    differences[sat]["S1_rec2"] = val2
                else:
                    differences[sat]["S1_rec1"] = None
                    differences[sat]["S1_rec2"] = None
    return differences


def compare_observations(
    file1: str, file2: str, max_time_diff: float = 60.0
) -> list[dict]:
    """
    Compare time epochs between two observation JSON files.

    Args:
        file1: Path to first JSON file
        file2: Path to second JSON file
        max_time_diff: Maximum allowed time difference in seconds for matching epochs
    """
    # Load JSON files
    obs1 = load_json_file(file1)
    obs2 = load_json_file(file2)

    data1 = obs1["data"]
    data2 = obs2["data"]

    print(f"File 1: {obs1['file']}")
    print(f"File 2: {obs2['file']}")
    print(f"Number of epochs in File 1: {len(data1)}")
    print(f"Number of epochs in File 2: {len(data2)}")
    print()
    print("Time matching results:")
    print("-" * 80)

    out_data = []
    # For each time in file1, find closest time in file2
    for idx1, entry1 in enumerate(data1):
        time1 = entry1["time"]
        idx2, time2 = find_closest_time_index(time1, data2)

        time_diff = abs((time1 - time2).total_seconds())
        if time_diff > max_time_diff:
            continue  # Skip if time difference is greater than 1 minute

        # print(
        #    f"obs1: {idx1:4d} {entry1['time']}  obs2: {idx2:4d} {data2[idx2]['time']}  (diff: {time_diff:.3f}s)"
        # )

        # Compare ambiguities for common satellites
        ambig_diff = compare_ambiguities(data1[idx1], data2[idx2])

        if ambig_diff:
            # print(f"  Common satellites: {', '.join(ambig_diff.keys())}")
            # Display differences for each satellite
            # for sat, diffs in ambig_diff.items():
            # print(f"    {sat}:")
            # for key, diff in diffs.items():
            #    if diff is not None:
            #        print(f"      {key}: {diff:+.6f}")
            #    else:
            #        print(f"      {key}: N/A (one or both values are null)")
            out_data.append(
                {
                    "obs1_index": idx1,
                    "obs2_index": idx2,
                    "time": entry1["time"],
                    "time_ref": data2[idx2]["time"],
                    "ambiguity_differences": ambig_diff,
                }
            )
        # else:
        #    print("  No common satellites")
    return out_data


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Compare time epochs between two GNSS observation JSON files"
    )
    parser.add_argument("file1", help="Path to first JSON file")
    parser.add_argument("file2", help="Path to second JSON file")
    parser.add_argument(
        "-o",
        "--outdir",
        default="./outfigs/",
        help="Directory to write output figure files (default: ./outfigs)",
    )

    args = parser.parse_args()

    file1 = args.file1
    file2 = args.file2
    output_figdir = Path(args.outdir)

    # Check if files exist
    if not Path(file1).exists():
        print(f"Error: {file1} not found")
        return

    if not Path(file2).exists():
        print(f"Error: {file2} not found")
        return
    output_figdir.mkdir(parents=True, exist_ok=True)
    Path(output_figdir / "single").mkdir(parents=True, exist_ok=True)
    Path(output_figdir / "diff").mkdir(parents=True, exist_ok=True)
    Path(output_figdir / "diffdiff").mkdir(parents=True, exist_ok=True)

    data = compare_observations(file1, file2)

    # Extract satellite pairs from data
    sat_pair_lists: dict[str, list[tuple[str, str]]] = {}
    sat_pair_lists["G"] = [
        ("G12", "G10"),
        ("G12", "G15"),
        ("G12", "G23"),
        ("G12", "G24"),
        ("G12", "G25"),
    ]
    #    for entry in data:
    #        for sat in entry["ambiguity_differences"].keys():
    #            if sat not in sat_pair_list:
    #                sat_pair_list.append(sat)

    # Optionally, save output data to a JSON file
    output_filepath = output_figdir / "comparison_output.json"
    with open(str(output_filepath), "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            default=lambda obj: obj.strftime("%Y-%m-%dT%H:%M:%S.%f")
            if isinstance(obj, datetime)
            else str(obj),
        )
    print(f"Comparison data saved to {output_filepath}")

    # Plotting
    for sat1, sat2 in sat_pair_lists["G"]:
        fig, axes = plot_obs(data, sat1, sat2)
        fig.savefig(
            output_figdir / "diffdiff" / f"DD_ambiguity_{sat1}_{sat2}.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close(fig)


if __name__ == "__main__":
    main()
