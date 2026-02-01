"""Ambiguity-related computations from RINEX observations.

Functions here operate on xarray Datasets returned by georinex.
"""

from __future__ import annotations

import xarray as xr

from app.gnss.constants import (
    CLIGHT,
    L1_FREQ,
    L2_FREQ,
    E5A_FREQ,
    wlen_L1,
    wlen_L2,
)


def get_widelane_ambiguity(
    rnxobs: xr.Dataset,
    satname: str,
    pr_l1_code: str = "C1C",
    cp_l1_code: str = "L1C",
    pr_l2_code: str = "C2X",
    cp_l2_code: str = "L2X",
) -> xr.DataArray:
    """Compute wide-lane ambiguity for a given satellite.

    Returns a tuple of (time, ambiguity DataArray).

    Args:
        rnxobs: RINEX observation dataset
        satname: Satellite name (e.g., 'G01')
        pr_l1_code: Pseudorange observation code for L1 (e.g., 'C1C', 'C1I', 'C1X')
        cp_l1_code: Carrier phase observation code for L1 (e.g., 'L1C', 'L1I', 'L1X')
        pr_l2_code: Pseudorange observation code for L2 (e.g., 'C2X', 'C2W', 'C2C')
        cp_l2_code: Carrier phase observation code for L2 (e.g., 'L2X', 'L2W', 'L2C')
    Returns:
        wide-lane ambiguity DataArray
    """
    pr_l1 = rnxobs[pr_l1_code].sel(sv=satname)
    cp_l1 = rnxobs[cp_l1_code].sel(sv=satname)
    pr_l2 = rnxobs[pr_l2_code].sel(sv=satname)
    cp_l2 = rnxobs[cp_l2_code].sel(sv=satname)

    if satname[0] in ["G", "J"] and pr_l2_code[0:2] == "C2" and cp_l2_code[0:2] == "L2":
        wl_wlen = CLIGHT / (L1_FREQ - L2_FREQ)
        nl_pr = (
            L1_FREQ / (L1_FREQ + L2_FREQ) * pr_l1
            + L2_FREQ / (L1_FREQ + L2_FREQ) * pr_l2
        )
        wl_cp = cp_l1 - cp_l2
        amb_wl = wl_cp - nl_pr / wl_wlen
    elif satname[0] == "E":
        # Galileo E1-E5a
        wl_wlen = CLIGHT / (L1_FREQ - E5A_FREQ)
        nl_pr = (
            L1_FREQ / (L1_FREQ + E5A_FREQ) * pr_l1
            + E5A_FREQ / (L1_FREQ + E5A_FREQ) * pr_l2
        )
        wl_cp = cp_l1 - cp_l2
        amb_wl = wl_cp - nl_pr / wl_wlen
    else:
        raise ValueError(
            "Wide-lane ambiguity could not be computed for the given satellite and codes."
        )
    return amb_wl


def get_narrowlane_ambiguity(
    rnxobs: xr.Dataset,
    satname: str,
    amb_wl_mean: float,
    pr_l1_code: str = "C1C",
    cp_l1_code: str = "L1C",
    pr_l2_code: str = "C2X",
    cp_l2_code: str = "L2X",
) -> xr.DataArray:
    """Compute narrow-lane ambiguity N1 using iono-free combination and wide-lane mean.

    Args:
        rnxobs: RINEX observation dataset
        satname: Satellite name (e.g., 'G01')
        amb_wl_mean: Mean wide-lane ambiguity value
        pr_l1_code: Pseudorange observation code for L1 (e.g., 'C1C', 'C1I', 'C1X')
        cp_l1_code: Carrier phase observation code for L1 (e.g., 'L1C', 'L1I', 'L1X')
        pr_l2_code: Pseudorange observation code for L2 (e.g., 'C2X', 'C2W', 'C2C')
        cp_l2_code: Carrier phase observation code for L2 (e.g., 'L2X', 'L2W', 'L2C')
    Returns:
        narrow-lane ambiguity DataArray
    """
    pr_l1 = rnxobs[pr_l1_code].sel(sv=satname)
    cp_l1 = rnxobs[cp_l1_code].sel(sv=satname)
    pr_l2 = rnxobs[pr_l2_code].sel(sv=satname)
    cp_l2 = rnxobs[cp_l2_code].sel(sv=satname)

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
    return amb_n1


def get_ionospheric_ambiguity(
    rnxobs: xr.Dataset,
    satname: str,
    pr_l1_code: str = "C1C",
    cp_l1_code: str = "L1C",
    pr_l2_code: str = "C2X",
    cp_l2_code: str = "L2X",
) -> xr.DataArray:
    """Compute iono-free ambiguity using L1/L2 combinations.

    Args:
        rnxobs: RINEX observation dataset
        satname: Satellite name (e.g., 'G01')
        pr_l1_code: Pseudorange observation code for L1 (e.g., 'C1C', 'C1I', 'C1X')
        cp_l1_code: Carrier phase observation code for L1 (e.g., 'L1C', 'L1I', 'L1X')
        pr_l2_code: Pseudorange observation code for L2 (e.g., 'C2X', 'C2W', 'C2C')
        cp_l2_code: Carrier phase observation code for L2 (e.g., 'L2X', 'L2W', 'L2C')
    Returns:
        ionospheric ambiguity DataArray
    """
    pr_l1 = rnxobs[pr_l1_code].sel(sv=satname)
    cp_l1 = rnxobs[cp_l1_code].sel(sv=satname)
    pr_l2 = rnxobs[pr_l2_code].sel(sv=satname)
    cp_l2 = rnxobs[cp_l2_code].sel(sv=satname)

    # if pr_l2_code[0:2] == "C2" and pr_l2_code != "C2X":
    #    # Adjust for different L2 pseudorange codes
    #     pr_l2 += 0.244 * wlen_L2  # Example adjustment value; may vary by code
    amb_iono = None
    if satname[0] in ["G", "J"] and pr_l2_code[0:2] == "C2" and cp_l2_code[0:2] == "L2":
        pr_if = (L1_FREQ**2 * pr_l1 - L2_FREQ**2 * pr_l2) / (L1_FREQ**2 - L2_FREQ**2)
        cp_if = (L1_FREQ**2 * wlen_L1 * cp_l1 - L2_FREQ**2 * wlen_L2 * cp_l2) / (
            L1_FREQ**2 - L2_FREQ**2
        )
        amb_iono = (cp_if - pr_if) / (
            (L1_FREQ**2) / (L1_FREQ**2 - L2_FREQ**2) * wlen_L1
            + (L2_FREQ**2) / (L1_FREQ**2 - L2_FREQ**2) * wlen_L2
        )
    elif satname[0] == "E":
        # Galileo E1-E5a
        L5_FREQ = 1.17645e9
        wlen_L5 = CLIGHT / L5_FREQ
        pr_if = (L1_FREQ**2 * pr_l1 - L5_FREQ**2 * pr_l2) / (L1_FREQ**2 - L5_FREQ**2)
        cp_if = (L1_FREQ**2 * wlen_L1 * cp_l1 - L5_FREQ**2 * wlen_L5 * cp_l2) / (
            L1_FREQ**2 - L5_FREQ**2
        )
        amb_iono = (cp_if - pr_if) / (
            (L1_FREQ**2) / (L1_FREQ**2 - L5_FREQ**2) * wlen_L1
            + (L5_FREQ**2) / (L1_FREQ**2 - L5_FREQ**2) * wlen_L5
        )
    else:
        raise NotImplementedError(
            "Ionospheric ambiguity could not be computed for the given satellite and codes."
        )
    return amb_iono


def calculate_double_difference_widelane_ambiguity(
    rnxobs1: xr.Dataset,
    rnxobs2: xr.Dataset,
    satname1: str,
    satname2: str,
    obs1_l1_code: str = "C",
    obs1_l2_code: str = "X",
    obs2_l1_code: str = "C",
    obs2_l2_code: str = "X",
    time_synchronize: bool = True,
) -> xr.DataArray:
    """Calculate double difference wide-lane ambiguity between two receivers and two satellites.

    Args:
        rnxobs1: GNSS observation data from receiver 1
        rnxobs2: GNSS observation data from receiver 2
        satname1: Satellite name 1
        satname2: Satellite name 2
        obs1_l1_code: Signal code for L1 in receiver 1
        obs1_l2_code: Signal code for L2 in receiver 1
        obs2_l1_code: Signal code for L1 in receiver 2
        obs2_l2_code: Signal code for L2 in receiver 2
        time_synchronize: bool = True, Whether to synchronize time between two datasets
    Returns:
        DataArray: Double difference wide-lane ambiguity
    """
    amb_sat1_rec1_wl = get_widelane_ambiguity(
        rnxobs1,
        satname1,
        f"C1{obs1_l1_code}",
        f"L1{obs1_l1_code}",
        f"C2{obs1_l2_code}",
        f"L2{obs1_l2_code}",
    )
    amb_sat2_rec1_wl = get_widelane_ambiguity(
        rnxobs1,
        satname2,
        f"C1{obs1_l1_code}",
        f"L1{obs1_l1_code}",
        f"C2{obs1_l2_code}",
        f"L2{obs1_l2_code}",
    )
    amb_sat1_rec2_wl = get_widelane_ambiguity(
        rnxobs2,
        satname1,
        f"C1{obs2_l1_code}",
        f"L1{obs2_l1_code}",
        f"C2{obs2_l2_code}",
        f"L2{obs2_l2_code}",
    )
    amb_sat2_rec2_wl = get_widelane_ambiguity(
        rnxobs2,
        satname2,
        f"C1{obs2_l1_code}",
        f"L1{obs2_l1_code}",
        f"C2{obs2_l2_code}",
        f"L2{obs2_l2_code}",
    )
    # difference between two receivers and two satellites
    if time_synchronize:
        amb_sat1_rec1_wl = amb_sat1_rec1_wl.drop_duplicates("time")
        amb_sat2_rec1_wl = amb_sat2_rec1_wl.drop_duplicates("time")
        amb_sat1_rec2_wl = amb_sat1_rec2_wl.sel(
            time=amb_sat1_rec1_wl.time, method="nearest"
        )
        amb_sat2_rec2_wl = amb_sat2_rec2_wl.sel(
            time=amb_sat2_rec1_wl.time, method="nearest"
        )
        amb_sat1_rec2_wl = amb_sat1_rec2_wl.drop_duplicates("time")
        amb_sat2_rec2_wl = amb_sat2_rec2_wl.drop_duplicates("time")
    amb_wl_sat12_rec12 = (amb_sat1_rec1_wl - amb_sat2_rec1_wl) - (
        amb_sat1_rec2_wl - amb_sat2_rec2_wl
    )
    return amb_wl_sat12_rec12


def calculate_double_difference_ionospheric_ambiguity(
    rnxobs1: xr.Dataset,
    rnxobs2: xr.Dataset,
    satname1: str,
    satname2: str,
    obs1_l1_code: str = "C",
    obs1_l2_code: str = "X",
    obs2_l1_code: str = "C",
    obs2_l2_code: str = "X",
    time_synchronize: bool = True,
) -> xr.DataArray:
    """Calculate double difference ionospheric ambiguity between two receivers and two satellites.

    Args:
        rnxobs1: GNSS observation data from receiver 1
        rnxobs2: GNSS observation data from receiver 2
        satname1: Satellite name 1
        satname2: Satellite name 2
        obs1_l1_code: Signal code for L1 in receiver 1
        obs1_l2_code: Signal code for L2 in receiver 1
        obs2_l1_code: Signal code for L1 in receiver 2
        obs2_l2_code: Signal code for L2 in receiver 2
        time_synchronize: bool = True, Whether to synchronize time between two datasets
    Returns:
        DataArray: Double difference ionospheric ambiguity
    """
    if satname1[0] != satname2[0]:
        raise ValueError(
            "Satellites must belong to the same constellation for ionospheric ambiguity calculation."
        )
    _, amb_sat1_rec1_iono = get_ionospheric_ambiguity(
        rnxobs1,
        satname1,
        f"C1{obs1_l1_code}",
        f"L1{obs1_l1_code}",
        f"C2{obs1_l2_code}",
        f"L2{obs1_l2_code}",
    )
    _, amb_sat2_rec1_iono = get_ionospheric_ambiguity(
        rnxobs1,
        satname2,
        f"C1{obs1_l1_code}",
        f"L1{obs1_l1_code}",
        f"C2{obs1_l2_code}",
        f"L2{obs1_l2_code}",
    )
    _, amb_sat1_rec2_iono = get_ionospheric_ambiguity(
        rnxobs2,
        satname1,
        f"C1{obs2_l1_code}",
        f"L1{obs2_l1_code}",
        f"C2{obs2_l2_code}",
        f"L2{obs2_l2_code}",
    )
    _, amb_sat2_rec2_iono = get_ionospheric_ambiguity(
        rnxobs2,
        satname2,
        f"C1{obs2_l1_code}",
        f"L1{obs2_l1_code}",
        f"C2{obs2_l2_code}",
        f"L2{obs2_l2_code}",
    )
    # difference between two receivers and two satellites
    if time_synchronize:
        amb_sat1_rec1_iono = amb_sat1_rec1_iono.drop_duplicates("time")
        amb_sat2_rec1_iono = amb_sat2_rec1_iono.drop_duplicates("time")
        amb_sat1_rec2_iono = amb_sat1_rec2_iono.sel(
            time=amb_sat1_rec1_iono.time, method="nearest"
        )
        amb_sat2_rec2_iono = amb_sat2_rec2_iono.sel(
            time=amb_sat2_rec1_iono.time, method="nearest"
        )
        amb_sat1_rec2_iono = amb_sat1_rec2_iono.drop_duplicates("time")
        amb_sat2_rec2_iono = amb_sat2_rec2_iono.drop_duplicates("time")
    amb_iono_sat12_rec12 = (amb_sat1_rec1_iono - amb_sat2_rec1_iono) - (
        amb_sat1_rec2_iono - amb_sat2_rec2_iono
    )
    return amb_iono_sat12_rec12


def calculate_double_difference(
    rnxobs1: xr.Dataset, rnxobs2: xr.Dataset, satellite_pair_list: list[tuple[str, str]]
) -> tuple[dict[str, xr.DataArray], dict[str, xr.DataArray]]:
    """Calculate double difference between two receivers and multiple satellite pairs.

    Args:
        rnxobs1: GNSS observation data from receiver 1
        rnxobs2: GNSS observation data from receiver 2
        satellite_pair_list: List of satellite name pairs

    Returns:
        A tuple containing:
            - dict mapping "sat1-sat2" to widelane ambiguity DataArray
            - dict mapping "sat1-sat2" to ionospheric ambiguity DataArray
    """
    all_wl: dict[str, xr.DataArray] = {}
    all_iono: dict[str, xr.DataArray] = {}
    for satname1, satname2 in satellite_pair_list:
        widelane_ambiguity = calculate_double_difference_widelane_ambiguity(
            rnxobs1, rnxobs2, satname1, satname2
        )
        all_wl[f"{satname1}-{satname2}"] = widelane_ambiguity
        ionospheric_ambiguity = calculate_double_difference_ionospheric_ambiguity(
            rnxobs1, rnxobs2, satname1, satname2
        )
        all_iono[f"{satname1}-{satname2}"] = ionospheric_ambiguity

    return all_wl, all_iono
