#!/usr/bin/env python3
"""
GPS Satellite Position Computation Program
Computes GPS satellite positions from RINEX navigation and observation files.
"""

import logging
import numpy as np
from datetime import datetime
from typing import Tuple, List
import argparse
import os
import sys

from app.gnss.satellite_signals import parse_rinex_observation_file
from app.gnss.ephemeris import (
    GPSEphemeris,
    read_rinex_nav,
    compute_satellite_position,
    OMEGA_E,
    C,
)

logger = logging.getLogger(__name__)


def compute_satellite_position_from_rcv_position(
    eph: GPSEphemeris, obs_time: datetime, rcv_pos: np.ndarray = None
) -> Tuple[np.ndarray, float]:
    """
    Precise satellite position computation with Earth rotation correction and signal transit time

    Args:
        eph: Ephemeris data
        obs_time: Observation time
        rcv_pos: Receiver position [x, y, z] (m) - if not specified, approximate calculation is used

    Returns:
        Tuple of satellite position [x, y, z] (m) and clock correction (s)
    """
    # Calculate with initial estimate
    sat_pos, clk = compute_satellite_position(eph, obs_time)
    print(eph.to_json())

    if rcv_pos is not None:
        # If receiver position is given, iteratively calculate signal transit time
        for _ in range(3):
            # Geometric range
            range_vec = sat_pos - rcv_pos
            geometric_range = np.linalg.norm(range_vec)

            # Signal transit time
            transit_time = geometric_range / C

            # Recalculate considering signal transit time
            sat_pos, clk = compute_satellite_position(eph, obs_time, transit_time)

        # Earth rotation correction (effect of Earth's rotation during signal propagation)
        rotation_angle = OMEGA_E * transit_time
        cos_rot = np.cos(rotation_angle)
        sin_rot = np.sin(rotation_angle)

        # Apply rotation matrix
        x_corrected = cos_rot * sat_pos[0] + sin_rot * sat_pos[1]
        y_corrected = -sin_rot * sat_pos[0] + cos_rot * sat_pos[1]
        z_corrected = sat_pos[2]

        sat_pos = np.array([x_corrected, y_corrected, z_corrected])

    return sat_pos, clk


def read_rinex_obs_header(obs_file: str) -> Tuple[datetime, List[str], np.ndarray]:
    """
    Read RINEX observation file header and first epoch data

    Args:
        obs_file: Observation file path

    Returns:
        First observation time, list of observed GPS satellites, approximate receiver position
    """
    # Get receiver position from header
    with open(obs_file, "r") as f:
        lines = f.readlines()

    rcv_pos = None
    i = 0
    while i < len(lines) and "END OF HEADER" not in lines[i]:
        if "APPROX POSITION XYZ" in lines[i]:
            x = float(lines[i][0:14])
            y = float(lines[i][14:28])
            z = float(lines[i][28:42])
            rcv_pos = np.array([x, y, z])
        i += 1

    # Define default signal code map for GPS
    signal_code_map = {
        "GPS": [["1", "C"], ["2", "W"], ["2", "X"], ["5", "X"]],
        "GLONASS": [["1", "C"], ["1", "P"], ["2", "C"], ["2", "P"]],
        "Galileo": [["1", "X"], ["5", "X"], ["7", "X"], ["8", "X"]],
        "QZSS": [["1", "C"], ["1", "X"], ["2", "X"], ["5", "X"]],
    }

    # Parse observation file using satellite_signals module
    try:
        epochs = parse_rinex_observation_file(obs_file, signal_code_map)
        if not epochs:
            raise ValueError("No epochs found in observation file")

        # Get first epoch
        first_epoch = epochs[0]
        obs_time = first_epoch.datetime

        # Extract GPS satellite IDs
        satellites = []
        for sat_obs in first_epoch.satellites_gps:
            sat_id = f"G{sat_obs.prn:02d}"
            satellites.append(sat_id)

        return obs_time, satellites, rcv_pos
    except Exception as e:
        raise RuntimeError(f"Failed to parse observation file: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="GPS Satellite Position Computation Program",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  python gps_satellite_position.py obs.obs nav.nav
  python gps_satellite_position.py -o output.txt obs.obs nav.nav
        """,
    )
    parser.add_argument("obs_file", help="RINEX observation file")
    parser.add_argument("nav_file", help="RINEX navigation file")
    parser.add_argument("-o", "--output", help="Output file (stdout if not specified)")

    args = parser.parse_args()

    # Check file existence
    if not os.path.exists(args.obs_file):
        print(f"Error: Observation file not found: {args.obs_file}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.nav_file):
        print(f"Error: Navigation file not found: {args.nav_file}", file=sys.stderr)
        sys.exit(1)

    # Read navigation file
    print(f"Reading navigation file: {args.nav_file}")
    ephemerides = read_rinex_nav(args.nav_file)
    print(f"  Loaded ephemeris for {len(ephemerides)} satellites")

    # Get time and satellite list from observation file
    print(f"Reading observation file: {args.obs_file}")
    obs_time, satellites, rcv_pos = read_rinex_obs_header(args.obs_file)

    if obs_time is None:
        print(
            "Error: Failed to get time information from observation file",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"  Observation time: {obs_time}")
    print(f"  Number of GPS satellites: {len(satellites)}")

    if rcv_pos is not None:
        print(
            f"  Receiver position (ECEF): X={rcv_pos[0]:.4f}, Y={rcv_pos[1]:.4f}, Z={rcv_pos[2]:.4f}"
        )

    # Determine output destination
    if args.output:
        outf = open(args.output, "w")
    else:
        outf = sys.stdout

    # Output header
    outf.write("=" * 80 + "\n")
    outf.write("GPS Satellite Position Computation Results\n")
    outf.write("=" * 80 + "\n")
    outf.write(f"Observation time: {obs_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    outf.write(f"Observation file: {args.obs_file}\n")
    outf.write(f"Navigation file: {args.nav_file}\n")
    if rcv_pos is not None:
        outf.write(
            f"Receiver position (ECEF): X={rcv_pos[0]:.4f}, Y={rcv_pos[1]:.4f}, Z={rcv_pos[2]:.4f}\n"
        )
    outf.write("-" * 80 + "\n\n")

    # Calculate position for each satellite
    for sat_id in satellites:
        if sat_id not in ephemerides:
            outf.write(f"{sat_id}: Ephemeris not found\n\n")
            continue

        # Select ephemeris closest to observation time
        eph_list = ephemerides[sat_id]
        best_eph = min(eph_list, key=lambda e: abs((obs_time - e.toc).total_seconds()))

        # Calculate satellite position (precise calculation if receiver position is available)
        if rcv_pos is not None:
            print("PRECIESE CALCULATION WITH EARTH ROTATION CORRECTION")
            pos, clk = compute_satellite_position_from_rcv_position(
                best_eph, obs_time, rcv_pos
            )
        else:
            pos, clk = compute_satellite_position(best_eph, obs_time)

        # Output results
        outf.write(f"Satellite: {sat_id}\n")
        outf.write(f"  Ephemeris time: {best_eph.toc.strftime('%Y-%m-%d %H:%M:%S')}\n")
        outf.write("  Position (ECEF) [m]:\n")
        outf.write(f"    X = {pos[0]:14.4f}\n")
        outf.write(f"    Y = {pos[1]:14.4f}\n")
        outf.write(f"    Z = {pos[2]:14.4f}\n")
        outf.write(f"  Distance (from origin) = {np.linalg.norm(pos):14.4f} m\n")
        outf.write(f"  Satellite clock correction = {clk:14.9e} s\n")
        outf.write("\n")

    if args.output:
        outf.close()
        print(f"\nResults written to: {args.output}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    main()
