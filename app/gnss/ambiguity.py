"""Ambiguity-related computations from RINEX observations.

Functions here operate on xarray Datasets returned by georinex.
"""

from __future__ import annotations

from typing import Tuple
import xarray as xr

from .constants import (
    CLIGHT,
    L1_FREQ,
    L2_FREQ,
    wlen_L1,
    wlen_L2,
)


def get_wineline_ambiguity(
    rnxobs: xr.Dataset, satname: str
) -> Tuple[xr.DataArray, xr.DataArray]:
    """Compute wide-lane ambiguity for a given satellite.

    Returns a tuple of (time, ambiguity DataArray).
    """
    pr_l1 = rnxobs["C1C"].sel(sv=satname)
    cp_l1 = rnxobs["L1C"].sel(sv=satname)
    pr_l2 = rnxobs["C2X"].sel(sv=satname)
    cp_l2 = rnxobs["L2X"].sel(sv=satname)
    time = rnxobs.time

    wl_wlen = CLIGHT / (L1_FREQ - L2_FREQ)
    nl_pr = (
        L1_FREQ / (L1_FREQ + L2_FREQ) * pr_l1 + L2_FREQ / (L1_FREQ + L2_FREQ) * pr_l2
    )
    wl_cp = cp_l1 - cp_l2
    amb_wl = wl_cp - nl_pr / wl_wlen
    return time, amb_wl


def get_narrowline_ambiguity(
    rnxobs: xr.Dataset, satname: str, amb_wl_mean: float
) -> Tuple[xr.DataArray, xr.DataArray]:
    """Compute narrow-lane ambiguity N1 using iono-free combination and wide-lane mean."""
    pr_l1 = rnxobs["C1C"].sel(sv=satname)
    cp_l1 = rnxobs["L1C"].sel(sv=satname)
    pr_l2 = rnxobs["C2X"].sel(sv=satname)
    cp_l2 = rnxobs["L2X"].sel(sv=satname)
    time = rnxobs.time

    pr_if = (L1_FREQ**2 * pr_l1 - L2_FREQ**2 * pr_l2) / (L1_FREQ**2 - L2_FREQ**2)
    cp_if = (L1_FREQ**2 * wlen_L1 * cp_l1 - L2_FREQ**2 * wlen_L2 * cp_l2) / (
        L1_FREQ**2 - L2_FREQ**2
    )
    amb_n1 = (
        cp_if
        - pr_if
        - (-(L2_FREQ**2)) / (L1_FREQ**2 - L2_FREQ**2) * wlen_L2 * amb_wl_mean
    ) / (
        (L1_FREQ**2) / (L1_FREQ**2 - L2_FREQ**2) * wlen_L1
        + (L2_FREQ**2) / (L1_FREQ**2 - L2_FREQ**2) * wlen_L2
    )
    return time, amb_n1


def get_ionospheric_ambiguity(
    rnxobs: xr.Dataset, satname: str
) -> Tuple[xr.DataArray, xr.DataArray]:
    """Compute iono-free ambiguity using L1/L2 combinations."""
    pr_l1 = rnxobs["C1C"].sel(sv=satname)
    cp_l1 = rnxobs["L1C"].sel(sv=satname)
    pr_l2 = rnxobs["C2X"].sel(sv=satname)
    cp_l2 = rnxobs["L2X"].sel(sv=satname)
    time = rnxobs.time

    pr_if = (L1_FREQ**2 * pr_l1 - L2_FREQ**2 * pr_l2) / (L1_FREQ**2 - L2_FREQ**2)
    cp_if = (L1_FREQ**2 * wlen_L1 * cp_l1 - L2_FREQ**2 * wlen_L2 * cp_l2) / (
        L1_FREQ**2 - L2_FREQ**2
    )
    amb_iono = (cp_if - pr_if) / (
        (L1_FREQ**2) / (L1_FREQ**2 - L2_FREQ**2) * wlen_L1
        + (L2_FREQ**2) / (L1_FREQ**2 - L2_FREQ**2) * wlen_L2
    )
    return time, amb_iono
