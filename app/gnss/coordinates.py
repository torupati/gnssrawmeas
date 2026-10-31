"""Coordinate conversion utilities for GNSS processing."""

from __future__ import annotations

import numpy as np

# WGS84 constants
WGS84_A = 6378137.0
WGS84_F = 1 / 298.257223563
WGS84_E2 = WGS84_F * (2 - WGS84_F)


def ecef_to_llh(pos: np.ndarray) -> np.ndarray:
    if not np.all(np.isfinite(pos)) or np.linalg.norm(pos) < 1.0:
        return np.array([0.0, 0.0, 0.0])
    x, y, z = pos
    lon = np.arctan2(y, x)
    r = np.hypot(x, y)
    lat = np.arctan2(z, r * (1 - WGS84_E2))

    for _ in range(5):
        sin_lat = np.sin(lat)
        N = WGS84_A / np.sqrt(1 - WGS84_E2 * sin_lat**2)
        h = r / np.cos(lat) - N
        lat = np.arctan2(z, r * (1 - WGS84_E2 * N / (N + h)))

    sin_lat = np.sin(lat)
    N = WGS84_A / np.sqrt(1 - WGS84_E2 * sin_lat**2)
    h = r / np.cos(lat) - N

    return np.array([np.degrees(lat), np.degrees(lon), h])


def ecef_to_enu_matrix(lat_deg: float, lon_deg: float) -> np.ndarray:
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)
    sin_lat = np.sin(lat)
    cos_lat = np.cos(lat)
    sin_lon = np.sin(lon)
    cos_lon = np.cos(lon)
    return np.array(
        [
            [-sin_lon, cos_lon, 0.0],
            [-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat],
            [cos_lat * cos_lon, cos_lat * sin_lon, sin_lat],
        ]
    )


def llh_to_ecef(llh: np.ndarray) -> np.ndarray:
    """Convert geodetic [lat_deg, lon_deg, h_m] to ECEF (m)."""
    lat = np.radians(llh[0])
    lon = np.radians(llh[1])
    h = llh[2]
    sin_lat = np.sin(lat)
    N = WGS84_A / np.sqrt(1 - WGS84_E2 * sin_lat**2)
    return np.array(
        [
            (N + h) * np.cos(lat) * np.cos(lon),
            (N + h) * np.cos(lat) * np.sin(lon),
            (N * (1 - WGS84_E2) + h) * sin_lat,
        ]
    )


def radii_of_curvature(lat_rad: float) -> tuple[float, float]:
    """Meridian (M) and prime vertical (N) radii of curvature (m) at a geodetic latitude."""
    w2 = 1 - WGS84_E2 * np.sin(lat_rad) ** 2
    M = WGS84_A * (1 - WGS84_E2) / w2**1.5
    N = WGS84_A / np.sqrt(w2)
    return float(M), float(N)
