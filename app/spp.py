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
from app.gnss.database import GnssDatabase
from app.gnss.satellite_signals import EpochObservations, parse_rinex_observation_file

logger = getLogger(__name__)

MU_GPS = 3.986005e14
OMEGA_E = 7.2921151467e-5
F_REL = -4.442807633e-10


@dataclass
class GpsNavMessage:
    sv: str
    toc: float
    toe: float
    week: Optional[int]
    af0: float
    af1: float
    af2: float
    sqrtA: float
    e: float
    i0: float
    Omega0: float
    omega: float
    M0: float
    delta_n: float
    OmegaDot: float
    iDot: float
    Cuc: float
    Cus: float
    Crc: float
    Crs: float
    Cic: float
    Cis: float
    tgd: float


@dataclass
class SppSolution:
    datetime: datetime
    position_ecef: np.ndarray
    position_llh: np.ndarray
    clock_bias_m: float
    num_sats: int
    residuals: np.ndarray


def datetime_to_gps_week_seconds(dt: datetime) -> tuple[int, float]:
    gps_epoch = datetime(1980, 1, 6)
    total_seconds = (dt - gps_epoch).total_seconds()
    week = int(total_seconds // 604800)
    sow = total_seconds - week * 604800
    return week, sow


def _wrap_time_diff(dt: float) -> float:
    if dt > 302400.0:
        return dt - 604800.0
    if dt < -302400.0:
        return dt + 604800.0
    return dt


def _parse_nav_fixed_values(
    line: str, start_index: int, count: int
) -> list[Optional[float]]:
    fields: list[Optional[float]] = []
    for idx in range(count):
        start = start_index + idx * 19
        end = start + 19
        chunk = line[start:end].replace("D", "E").strip()
        if not chunk:
            fields.append(None)
            continue
        try:
            fields.append(float(chunk))
        except ValueError:
            fields.append(None)
    return fields


def _parse_nav_epoch(line: str) -> Optional[datetime]:
    try:
        year = int(line[4:8])
        month = int(line[9:11])
        day = int(line[12:14])
        hour = int(line[15:17])
        minute = int(line[18:20])
        sec_str = line[21:23]
        if not sec_str.strip():
            return None
        sec = float(sec_str)
    except ValueError:
        tokens = line[3:].replace("D", "E").split()
        if len(tokens) < 6:
            return None
        try:
            year = int(tokens[0])
            month = int(tokens[1])
            day = int(tokens[2])
            hour = int(tokens[3])
            minute = int(tokens[4])
            sec = float(tokens[5])
        except ValueError:
            return None
    second_int = int(sec)
    micro = int(round((sec - second_int) * 1e6))
    return datetime(year, month, day, hour, minute, second_int, micro)


def _require_float(value: Optional[float]) -> float:
    if value is None:
        raise ValueError("Expected float, got None")
    return value


def parse_rinex_navigation_file(file_path: str) -> dict[str, list[GpsNavMessage]]:
    nav: dict[str, list[GpsNavMessage]] = {}
    with Path(file_path).open("r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    idx = 0
    while idx < len(lines):
        if "END OF HEADER" in lines[idx]:
            idx += 1
            break
        idx += 1

    while idx < len(lines):
        line0 = lines[idx]
        if not line0.strip():
            idx += 1
            continue
        sv = line0[:3].strip()
        if len(lines) - idx < 8:
            break

        epoch = _parse_nav_epoch(line0)
        if epoch is None:
            idx += 1
            continue

        line1 = lines[idx + 1]
        line2 = lines[idx + 2]
        line3 = lines[idx + 3]
        line4 = lines[idx + 4]
        line5 = lines[idx + 5]
        line6 = lines[idx + 6]
        # line7 = lines[idx + 7] # not used

        if not sv.startswith("G"):
            idx += 8
            continue

        nav.setdefault(sv, [])

        af0, af1, af2 = _parse_nav_fixed_values(line0, 23, 3)
        IODE, Crs, DeltaN, M0 = _parse_nav_fixed_values(line1, 4, 4)
        Cuc, e, Cus, sqrtA = _parse_nav_fixed_values(line2, 4, 4)
        Toe, Cic, Omega0, Cis = _parse_nav_fixed_values(line3, 4, 4)
        i0, Crc, omega, OmegaDot = _parse_nav_fixed_values(line4, 4, 4)
        iDot, CodesL2, GPSWeek, L2Pflag = _parse_nav_fixed_values(line5, 4, 4)
        SVacc, health, TGD, IODC = _parse_nav_fixed_values(line6, 4, 4)

        if any(
            val is None
            for val in [
                af0,
                af1,
                af2,
                sqrtA,
                e,
                i0,
                Omega0,
                omega,
                M0,
                DeltaN,
                OmegaDot,
                iDot,
                Cuc,
                Cus,
                Crc,
                Crs,
                Cic,
                Cis,
                Toe,
            ]
        ):
            idx += 8
            continue

        week, sow = datetime_to_gps_week_seconds(epoch)
        week_val = int(GPSWeek) if GPSWeek is not None else int(week)

        msg = GpsNavMessage(
            sv=sv,
            toc=sow,
            toe=float(_require_float(Toe)),
            week=week_val,
            af0=float(_require_float(af0)),
            af1=float(_require_float(af1)),
            af2=float(_require_float(af2)),
            sqrtA=float(_require_float(sqrtA)),
            e=float(_require_float(e)),
            i0=float(_require_float(i0)),
            Omega0=float(_require_float(Omega0)),
            omega=float(_require_float(omega)),
            M0=float(_require_float(M0)),
            delta_n=float(_require_float(DeltaN)),
            OmegaDot=float(_require_float(OmegaDot)),
            iDot=float(_require_float(iDot)),
            Cuc=float(_require_float(Cuc)),
            Cus=float(_require_float(Cus)),
            Crc=float(_require_float(Crc)),
            Crs=float(_require_float(Crs)),
            Cic=float(_require_float(Cic)),
            Cis=float(_require_float(Cis)),
            tgd=float(TGD) if TGD is not None else 0.0,
        )
        nav[sv].append(msg)
        idx += 8

    return nav


def select_navigation_message(
    nav_data: dict[str, list[GpsNavMessage]],
    sv: str,
    sow: float,
) -> Optional[GpsNavMessage]:
    messages = nav_data.get(sv, [])
    if not messages:
        return None
    return min(messages, key=lambda msg: abs(_wrap_time_diff(sow - msg.toe)))


def _solve_kepler(M: float, e: float) -> float:
    E = M
    for _ in range(10):
        f = E - e * np.sin(E) - M
        f_prime = 1 - e * np.cos(E)
        dE = -f / f_prime
        E += dE
        if abs(dE) < 1e-12:
            break
    return E


def broadcast_ecef_and_clock(
    nav: GpsNavMessage,
    sow: float,
) -> tuple[np.ndarray, float]:
    tk = _wrap_time_diff(sow - nav.toe)
    A = nav.sqrtA**2
    n0 = np.sqrt(MU_GPS / A**3)
    n = n0 + nav.delta_n
    M = nav.M0 + n * tk

    E = _solve_kepler(M, nav.e)
    v = np.arctan2(np.sqrt(1 - nav.e**2) * np.sin(E), np.cos(E) - nav.e)
    phi = v + nav.omega

    sin2p = np.sin(2 * phi)
    cos2p = np.cos(2 * phi)

    u = phi + nav.Cus * sin2p + nav.Cuc * cos2p
    r = A * (1 - nav.e * np.cos(E)) + nav.Crs * sin2p + nav.Crc * cos2p
    i = nav.i0 + nav.iDot * tk + nav.Cis * sin2p + nav.Cic * cos2p

    x_prime = r * np.cos(u)
    y_prime = r * np.sin(u)

    Omega = nav.Omega0 + (nav.OmegaDot - OMEGA_E) * tk - OMEGA_E * nav.toe

    cosO = np.cos(Omega)
    sinO = np.sin(Omega)
    cosi = np.cos(i)
    sini = np.sin(i)

    x = x_prime * cosO - y_prime * cosi * sinO
    y = x_prime * sinO + y_prime * cosi * cosO
    z = y_prime * sini

    dt = _wrap_time_diff(sow - nav.toc)
    dtsv = (
        nav.af0
        + nav.af1 * dt
        + nav.af2 * dt**2
        + F_REL * nav.e * nav.sqrtA * np.sin(E)
        - nav.tgd
    )

    return np.array([x, y, z]), dtsv


def compute_satellite_state(
    nav_data: dict[str, list[GpsNavMessage]],
    sv: str,
    recv_dt: datetime,
    pseudorange_m: float,
) -> Optional[tuple[np.ndarray, float]]:
    _, sow = datetime_to_gps_week_seconds(recv_dt)
    nav = select_navigation_message(nav_data, sv, sow)
    if nav is None:
        return None

    t_tx = sow - pseudorange_m / CLIGHT
    for _ in range(2):
        sat_pos, dtsv = broadcast_ecef_and_clock(nav, t_tx)
        t_tx = sow - (pseudorange_m + CLIGHT * dtsv) / CLIGHT

    sat_pos, dtsv = broadcast_ecef_and_clock(nav, t_tx)
    return sat_pos, dtsv


def tropospheric_delay(
    receiver_llh: np.ndarray, sat_pos: np.ndarray, recv_pos: np.ndarray
) -> float:
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

    pressure = 1013.25 * (1 - 2.2557e-5 * h) ** 5.2568
    temperature = 291.15 - 0.0065 * h
    vapor_pressure = 11.7

    zenith_delay = 0.002277 * (pressure + (1255 / temperature + 0.05) * vapor_pressure)
    return zenith_delay / np.sin(elev)


def apply_earth_rotation_correction(
    sat_pos: np.ndarray, travel_time: float
) -> np.ndarray:
    theta = OMEGA_E * travel_time
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    rotation = np.array([[cos_t, sin_t, 0.0], [-sin_t, cos_t, 0.0], [0.0, 0.0, 1.0]])
    return rotation @ sat_pos


def single_point_positioning(
    epochs: list[EpochObservations],
    nav_data: dict[str, list[GpsNavMessage]],
    max_iterations: int = 8,
) -> list[SppSolution]:
    solutions: list[SppSolution] = []
    receiver_pos = np.zeros(3)
    receiver_clock = 0.0

    for epoch in epochs:
        measurements = []
        for sat_id, sat_obs in epoch.iter_satellites():
            if not sat_id.startswith("G"):
                continue
            if "L1" not in sat_obs.signals:
                continue
            pr = sat_obs.signals["L1"].pseudorange
            if not np.isfinite(pr):
                continue
            state = compute_satellite_state(nav_data, sat_id, epoch.datetime, pr)
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
    parser.add_argument(
        "--database",
        type=str,
        default=None,
        help="Path to SQLite database file to save observations and solutions",
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

    nav_data = parse_rinex_navigation_file(str(nav_path))
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

    if args.database:
        db = GnssDatabase(args.database)
        db.save_epoch_observations(epochs)
        for sol in solutions:
            db.save_spp_solution(
                {
                    "position_ecef": sol.position_ecef.tolist(),
                    "position_llh": sol.position_llh.tolist(),
                    "clock_bias_m": sol.clock_bias_m,
                    "num_satellites": sol.num_sats,
                    "residuals": sol.residuals.tolist()
                    if sol.residuals.size > 0
                    else None,
                },
                sol.datetime,
            )
        logger.info("Saved observations and solutions to %s", args.database)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
