from typing import Optional
from logging import getLogger

import numpy as np
from georinex import rinexobs

logger = getLogger(__name__)

# from logre import logger
# logger = logger.bind(module="satellite_signals")
# logger = logger.opt(depth=1)


def get_available_signal_code(rnxobs, satname: str, freq_prefix: str):
    """
    Get available signal code for a given frequency prefix (e.g., 'L5', 'L2', 'L1').
    Returns the signal code suffix (e.g., 'X', 'I', 'Q', 'C') if available.

    Args:
        rnxobs: RINEX observation data
        satname: Satellite name (e.g., 'G01')
        freq_prefix: Frequency prefix (e.g., 'L5', 'L2', 'L1')

    Returns:
        Signal code suffix (e.g., 'X', 'I', 'Q') or None if not available
    """
    # Check available observation types
    available_obs = list(rnxobs.data_vars)

    # Find carrier phase observations starting with the frequency prefix
    carrier_phases = [obs for obs in available_obs if obs.startswith(freq_prefix)]

    if not carrier_phases:
        return None

    # Priority order for signal codes (prefer I, then X, then Q, then others)
    priority_codes = ["I", "X", "Q", "C"]

    # First, try priority codes
    for code in priority_codes:
        cp_obs = f"{freq_prefix}{code}"
        if cp_obs in carrier_phases:
            try:
                data = rnxobs[cp_obs].sel(sv=satname)
                if not data.isnull().all():
                    # Extract frequency number (e.g., '5' from 'L5')
                    freq_num = freq_prefix[1:]

                    # Check if corresponding pseudorange and doppler exist
                    pr_obs = f"C{freq_num}{code}"
                    dp_obs = f"D{freq_num}{code}"

                    if pr_obs in available_obs and dp_obs in available_obs:
                        return code
            except (KeyError, ValueError):
                continue

    # If no priority code works, try any available carrier phase
    for cp_obs in carrier_phases:
        try:
            data = rnxobs[cp_obs].sel(sv=satname)
            if not data.isnull().all():
                signal_code = cp_obs[len(freq_prefix) :]
                freq_num = freq_prefix[1:]

                pr_obs = f"C{freq_num}{signal_code}"
                dp_obs = f"D{freq_num}{signal_code}"

                if pr_obs in available_obs and dp_obs in available_obs:
                    return signal_code
        except (KeyError, ValueError):
            continue

    return None


def get_satellites_sorted_by_signal_strength(
    rnxobs: rinexobs, signal_type: str = "S1C", constellation: Optional[str] = None
) -> dict:
    """
    Sort satellites by signal strength for each epoch.

    Args:
        rnxobs (rinexobs): GNSS observation data
        signal_type (str): Signal strength indicator (default: "S1C")
        constellation (str): Constellation type filter (e.g., "G", "J", "E").
                           None for all constellations.

    Returns:
        dict: Dictionary with time as keys and list of (satellite, signal_strength)
              tuples sorted by signal strength (descending order) as values.
              Example: {
                  np.datetime64('2023-01-01T00:00:00'): [('G01', 45.0), ('G02', 43.5), ...],
                  ...
              }
    """
    # Get signal strength data
    if signal_type not in rnxobs:
        raise ValueError(
            f"Signal type '{signal_type}' not found in RINEX observation data"
        )

    signal_data = rnxobs[signal_type]

    # Get satellite list
    sv_list = [str(s) for s in rnxobs.sv.values]

    # Filter by constellation
    if constellation and constellation != "a":
        sv_list = [sv for sv in sv_list if sv.startswith(constellation)]

    # Process for each epoch
    sorted_by_epoch = {}

    for time_idx, time_val in enumerate(rnxobs.time.values):
        satellite_strengths = []

        for sv in sv_list:
            try:
                # Get signal strength
                strength = float(signal_data.sel(sv=sv, time=time_val).values)

                # Add to list only if not NaN
                if not np.isnan(strength):
                    satellite_strengths.append((sv, strength))
            except (KeyError, ValueError):
                # Skip if satellite data does not exist
                continue

        # Sort in descending order by signal strength
        satellite_strengths.sort(key=lambda x: x[1], reverse=True)
        sorted_by_epoch[time_val] = satellite_strengths

    return sorted_by_epoch


def get_satellite_pairs_by_signal_strength(
    rnxobs: rinexobs,
    signal_type: str = "S1C",
    constellation: Optional[str] = None,
    top_n: Optional[int] = None,
) -> list[tuple[str, str]]:
    """
    Generate satellite pairs based on signal strength.

    Create pairs with other satellites using the satellite with the highest signal strength at each epoch as a reference.

    Args:
        rnxobs (rinexobs): GNSS observation data
        signal_type (str): Signal strength indicator (default: "S1C")
        constellation (str): Constellation type filter (e.g., "G", "J", "E")
        top_n (int): Consider only top N satellites. None for all satellites.

    Returns:
        list: List of satellite pairs sorted by combined signal strength.
              Example: [('G01', 'G02'), ('G01', 'G03'), ...]
    """
    sorted_by_epoch = get_satellites_sorted_by_signal_strength(
        rnxobs, signal_type, constellation
    )

    # Calculate average signal strength across all epochs
    satellite_avg_strength_lists: dict[str, list[float]] = {}

    for time_val, sat_list in sorted_by_epoch.items():
        for sv, strength in sat_list:
            if sv not in satellite_avg_strength_lists:
                satellite_avg_strength_lists[sv] = []
            satellite_avg_strength_lists[sv].append(strength)

    # Calculate average
    satellite_avg_strength: dict[str, float] = {}
    for sv in satellite_avg_strength_lists:
        satellite_avg_strength[sv] = float(np.mean(satellite_avg_strength_lists[sv]))

    # Sort by average signal strength
    sorted_satellites = sorted(
        satellite_avg_strength.items(), key=lambda x: x[1], reverse=True
    )

    if top_n:
        sorted_satellites = sorted_satellites[:top_n]

    # Generate satellite pairs (using the strongest satellite as reference)
    if len(sorted_satellites) < 2:
        logger.warning("Not enough satellites to create pairs")
        return []

    reference_sat = sorted_satellites[0][0]
    pairs = []

    for sv, _ in sorted_satellites[1:]:
        pairs.append((reference_sat, sv))

    return pairs
