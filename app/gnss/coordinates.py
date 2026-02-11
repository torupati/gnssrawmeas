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
