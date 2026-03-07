"""Single Point Positioning (SPP) using RINEX observation and navigation files."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from logging import getLogger, basicConfig, INFO
from pathlib import Path
from typing import Optional

import numpy as np

from app.gnss.constants import CLIGHT
from app.gnss.coordinates import ecef_to_enu_matrix, ecef_to_llh
from app.gnss.ephemeris import (
    read_rinex_nav,
    compute_satellite_state,
    GPSEphemeris,
    datetime_to_gps_week_seconds,
)
from app.gnss.satellite_signals import EpochObservations, parse_rinex_observation_file

logger = getLogger(__name__)

OMEGA_E = 7.2921151467e-5


@dataclass
class SppSolution:
    datetime: datetime
    position_ecef: np.ndarray
    position_llh: np.ndarray
    clock_bias_m: float
    num_sats: int
    residuals: np.ndarray


def select_ephemeris(
    nav_data: dict[str, list[GPSEphemeris]],
    sv: str,
    sow: float,
) -> Optional[GPSEphemeris]:
    """Select the best ephemeris message for a given satellite and time."""
    messages = nav_data.get(sv, [])
    if not messages:
        return None
    # Return the ephemeris with the closest toe to sow
    return min(
        messages, key=lambda msg: abs((sow - msg.toe + 302400) % 604800 - 302400)
    )


def tropospheric_delay(
    receiver_llh: np.ndarray, sat_pos: np.ndarray, recv_pos: np.ndarray
) -> float:
    """
    Calculate tropospheric delay correction for the signal path.

    Estimates the delay of GNSS signals propagating through the troposphere
    using a simplified model based on receiver altitude, elevation angle,
    and standard atmospheric parameters.

    Args:
        receiver_llh: Receiver position in geodetic coordinates [lat, lon, h]
                     (radians, radians, meters)
        sat_pos: Satellite position in ECEF coordinates (meters)
        recv_pos: Receiver position in ECEF coordinates (meters)

    Returns:
        Tropospheric delay in meters. Returns 0.0 if:
        - Receiver position is invalid (norm < 1.0 m)
        - Altitude is outside valid range (-1000 to 100000 m)
        - Satellite elevation angle is below 5 degrees
        - Atmospheric calculation would be invalid
    """
    if np.linalg.norm(recv_pos) < 1.0:
        return 0.0

    lat, lon, h = receiver_llh
    if not np.isfinite(h) or h < -1000.0 or h > 1e5:
        return 0.0
    enu = ecef_to_enu_matrix(lat, lon) @ (sat_pos - recv_pos)
    east, north, up = enu
    horiz = np.hypot(east, north)
    elev = np.arctan2(up, horiz)
    if elev <= np.radians(5.0):
        return 0.0

    base = 1 - 2.2557e-5 * h
    logger.debug(f"Base: {base}, Elev: {np.degrees(elev):.2f} deg")
    if base <= 0:
        return 0.0
    pressure = 1013.25 * (base**5.2568)
    temperature = 291.15 - 0.0065 * h
    vapor_pressure = 11.7

    zenith_delay = 0.002277 * (pressure + (1255 / temperature + 0.05) * vapor_pressure)
    return zenith_delay / np.sin(elev)


def apply_earth_rotation_correction(
    sat_pos: np.ndarray, travel_time: float
) -> np.ndarray:
    """
    Apply Earth rotation correction to satellite position.

    Corrects the satellite position in ECEF coordinates to account for
    Earth's rotation during signal travel time. This is necessary because
    the satellite coordinates at transmission time must be rotated to match
    the Earth's orientation at reception time.

    Args:
        sat_pos: Satellite position in ECEF coordinates at transmission time
                (meters, 3-element array [x, y, z])
        travel_time: Signal travel time from satellite to receiver (seconds)

    Returns:
        Corrected satellite position in ECEF coordinates (meters)
    """
    theta = OMEGA_E * travel_time
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    rotation = np.array([[cos_t, sin_t, 0.0], [-sin_t, cos_t, 0.0], [0.0, 0.0, 1.0]])
    return rotation @ sat_pos


def single_point_positioning(
    epochs: list[EpochObservations],
    nav_data: dict[str, list[GPSEphemeris]],
    max_iterations: int = 8,
) -> list[SppSolution]:
    solutions: list[SppSolution] = []
    receiver_pos = np.zeros(3)
    receiver_clock = 0.0

    for epoch in epochs:
        measurements = []
        _, sow = datetime_to_gps_week_seconds(epoch.datetime)

        for sat_id, sat_obs in epoch.iter_satellites():
            if not sat_id.startswith("G"):
                continue
            if "L1" not in sat_obs.signals:
                continue
            pr = sat_obs.signals["L1"].pseudorange
            if not np.isfinite(pr):
                continue

            # Select the best ephemeris for this satellite
            nav = select_ephemeris(nav_data, sat_id, sow)
            if nav is None:
                continue

            # Compute satellite state using ephemeris module
            state = compute_satellite_state(nav, epoch.datetime, pr)
            if state is None:
                continue
            sat_pos, dtsv = state
            if not np.all(np.isfinite(sat_pos)) or not np.isfinite(dtsv):
                continue
            measurements.append((sat_id, sat_pos, dtsv, pr))

        if len(measurements) < 4:
            solutions.append(
                SppSolution(
                    datetime=epoch.datetime,
                    position_ecef=receiver_pos.copy(),
                    position_llh=ecef_to_llh(receiver_pos),
                    clock_bias_m=receiver_clock,
                    num_sats=len(measurements),
                    residuals=np.array([]),
                )
            )
            continue

        last_H = None
        last_v = None
        last_dx = None
        for _ in range(max_iterations):
            H_rows = []
            v_rows = []
            for _, sat_pos, dtsv, pr in measurements:
                rho = np.linalg.norm(sat_pos - receiver_pos)
                if rho <= 0 or not np.isfinite(rho):
                    continue
                travel_time = rho / CLIGHT
                sat_corr = apply_earth_rotation_correction(sat_pos, travel_time)
                if not np.all(np.isfinite(sat_corr)):
                    continue
                rho = np.linalg.norm(sat_corr - receiver_pos)
                if rho <= 0 or not np.isfinite(rho):
                    continue

                receiver_llh = ecef_to_llh(receiver_pos)
                tropo = tropospheric_delay(receiver_llh, sat_corr, receiver_pos)
                if not np.isfinite(tropo):
                    tropo = 0.0

                predicted = rho + receiver_clock - CLIGHT * dtsv + tropo
                v = pr - predicted
                if not np.isfinite(v):
                    continue
                H = (receiver_pos - sat_corr) / rho
                if not np.all(np.isfinite(H)):
                    continue
                H_rows.append([H[0], H[1], H[2], 1.0])
                v_rows.append(v)

            if len(H_rows) < 4:
                break

            H_mat = np.array(H_rows)
            v_vec = np.array(v_rows)
            dx, *_ = np.linalg.lstsq(H_mat, v_vec, rcond=None)
            last_H = H_mat
            last_v = v_vec
            last_dx = dx

            receiver_pos += dx[:3]
            receiver_clock += dx[3]

            if np.linalg.norm(dx[:3]) < 1e-3 and abs(dx[3]) < 1e-3:
                break

        if last_H is not None and last_v is not None and last_dx is not None:
            residuals = last_v - last_H @ last_dx
        else:
            residuals = np.array([])
        solutions.append(
            SppSolution(
                datetime=epoch.datetime,
                position_ecef=receiver_pos.copy(),
                position_llh=ecef_to_llh(receiver_pos),
                clock_bias_m=receiver_clock,
                num_sats=len(measurements),
                residuals=residuals,
            )
        )

    return solutions


def main() -> int:
    parser = argparse.ArgumentParser(description="Single Point Positioning (SPP)")
    parser.add_argument("rinex_obs", type=str, help="RINEX observation file")
    parser.add_argument("rinex_nav", type=str, help="RINEX navigation file")
    parser.add_argument(
        "--signal-code-map",
        type=str,
        default=str(Path(__file__).parent / ".signal_code_map.json"),
        help="Path to signal code map JSON",
    )
    parser.add_argument(
        "--max-epochs",
        type=int,
        default=0,
        help="Limit number of epochs processed (0 = all)",
    )

    args = parser.parse_args()
    basicConfig(level=INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    obs_path = Path(args.rinex_obs)
    nav_path = Path(args.rinex_nav)
    if not obs_path.exists() or not nav_path.exists():
        logger.error("Missing RINEX files: %s %s", obs_path, nav_path)
        return 1

    with Path(args.signal_code_map).open("r", encoding="utf-8") as f:
        signal_code_map = json.load(f)

    epochs = parse_rinex_observation_file(str(obs_path), signal_code_map)
    if args.max_epochs > 0:
        epochs = epochs[: args.max_epochs]

    nav_data = read_rinex_nav(str(nav_path))
    solutions = single_point_positioning(epochs, nav_data)

    for sol in solutions:
        lat, lon, h = sol.position_llh
        logger.info(
            "%s lat=%.8f lon=%.8f h=%.3f m clk=%.3f m sats=%d",
            sol.datetime.isoformat(),
            lat,
            lon,
            h,
            sol.clock_bias_m,
            sol.num_sats,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
