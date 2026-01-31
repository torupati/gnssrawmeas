from typing import Optional
from logging import getLogger
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

import georinex as gr
from georinex import rinexobs

from app.gnss.ambiguity import get_ionospheric_ambiguity, get_widelane_ambiguity
from app.gnss.constants import (
    CLIGHT,
    L1_FREQ,
    L2_FREQ,
    L5_FREQ,
    E5B_FREQ,
    E6_FREQ,
    wlen_L1,
    wlen_L2,
    wlen_L5,
    wlen_L7,
    wlen_L8,
)

logger = getLogger(__name__)

# Suppress FutureWarnings from xarray/georinex
warnings.filterwarnings("ignore", category=FutureWarning, module="georinex")
warnings.filterwarnings("ignore", category=FutureWarning, module="xarray")


@dataclass
class SatelliteSignalObservation:
    pseudorange: float  # in meters
    carrier_phase: float  # in cycles
    doppler_: float  # in Hz
    snr: float  # in dB-Hz


@dataclass
class AmbiguityObservation:
    widelane: float  # in cycle
    ionofree: float  # in cycle


@dataclass
class SatelliteObservation:
    prn: int
    signals: dict  # key: band (str), value: SatelliteSignalObservation
    ambiguities: (
        dict  # key: combination (str like "L1_L2"), value: AmbiguityObservation
    )

    def add_signal_observation(
        self, band_name: str, signal_obs: SatelliteSignalObservation
    ):
        self.signals[band_name] = signal_obs


@dataclass
class EpochObservations:
    datetime: datetime
    satellites_gps: list[SatelliteObservation]
    satellites_qzss: list[SatelliteObservation]
    satellites_galileo: list[SatelliteObservation]
    satellites_glonass: list[SatelliteObservation]


band_frequencies = {
    "L1": 1575.42e6,
    "L2": 1227.60e6,
    "L5": 1176.45e6,
}
band_names = {
    "L1": "L1",
    "L2": "L2",
    "L5": "L5",
}


def compute_dual_frequency_ambiguity(
    pr_f1: float,
    cp_f1: float,
    pr_f2: float,
    cp_f2: float,
    freq1: float,
    freq2: float,
    wlen1: float,
    wlen2: float,
) -> AmbiguityObservation:
    """
    Compute widelane and ionofree ambiguity for dual-frequency observations.

    Args:
        pr_f1: Pseudorange for frequency 1 (meters)
        cp_f1: Carrier phase for frequency 1 (cycles)
        pr_f2: Pseudorange for frequency 2 (meters)
        cp_f2: Carrier phase for frequency 2 (cycles)
        freq1: Frequency 1 (Hz)
        freq2: Frequency 2 (Hz)
        wlen1: Wavelength 1 (meters)
        wlen2: Wavelength 2 (meters)
    Returns:
        AmbiguityObservation with widelane and ionofree ambiguities in cycles
    """
    # Compute widelane ambiguity (cycles)
    wl_wlen = CLIGHT / (freq1 - freq2)
    nl_pr = freq1 / (freq1 + freq2) * pr_f1 + freq2 / (freq1 + freq2) * pr_f2
    wl_cp = cp_f1 - cp_f2
    amb_wl = wl_cp - nl_pr / wl_wlen

    # Compute ionofree ambiguity (cycles)
    pr_if = (freq1**2 * pr_f1 - freq2**2 * pr_f2) / (freq1**2 - freq2**2)
    cp_if = (freq1**2 * wlen1 * cp_f1 - freq2**2 * wlen2 * cp_f2) / (
        freq1**2 - freq2**2
    )
    amb_iono = (cp_if - pr_if) / (
        (freq1**2) / (freq1**2 - freq2**2) * wlen1
        + (freq2**2) / (freq1**2 - freq2**2) * wlen2
    )

    return AmbiguityObservation(widelane=amb_wl, ionofree=amb_iono)


def compute_ambiguities_for_satellite(
    sat_obs: SatelliteObservation, system_name: str
) -> dict:
    """
    Compute widelane and ionofree ambiguities for all available frequency pairs.

    For GPS/QZSS: Compute L1/L2 and L1/L5 if available
    For Galileo: Compute L1/L5, L1/L7, L1/L8 if available

    Args:
        sat_obs: SatelliteObservation with signals dict
        system_name: System name ("GPS", "QZSS", or "Galileo")
    Returns:
        Dict of {combination_name: AmbiguityObservation}
    """
    ambiguities = {}

    # GPS/QZSS: L1/L2 combination
    if system_name in ["GPS", "QZSS"]:
        if "L1" in sat_obs.signals and "L2" in sat_obs.signals:
            sig_l1 = sat_obs.signals["L1"]
            sig_l2 = sat_obs.signals["L2"]
            ambiguities["L1_L2"] = compute_dual_frequency_ambiguity(
                sig_l1.pseudorange,
                sig_l1.carrier_phase,
                sig_l2.pseudorange,
                sig_l2.carrier_phase,
                L1_FREQ,
                L2_FREQ,
                wlen_L1,
                wlen_L2,
            )

    # GPS/QZSS/Galileo: L1/L5 combination
    if system_name in ["GPS", "QZSS", "Galileo"]:
        if "L1" in sat_obs.signals and "L5" in sat_obs.signals:
            sig_l1 = sat_obs.signals["L1"]
            sig_l5 = sat_obs.signals["L5"]
            ambiguities["L1_L5"] = compute_dual_frequency_ambiguity(
                sig_l1.pseudorange,
                sig_l1.carrier_phase,
                sig_l5.pseudorange,
                sig_l5.carrier_phase,
                L1_FREQ,
                L5_FREQ,
                wlen_L1,
                wlen_L5,
            )

    # Galileo: L1/L7 combination (E1/E5B)
    if system_name == "Galileo":
        if "L1" in sat_obs.signals and "L7" in sat_obs.signals:
            sig_l1 = sat_obs.signals["L1"]
            sig_l7 = sat_obs.signals["L7"]
            ambiguities["L1_L7"] = compute_dual_frequency_ambiguity(
                sig_l1.pseudorange,
                sig_l1.carrier_phase,
                sig_l7.pseudorange,
                sig_l7.carrier_phase,
                L1_FREQ,
                E5B_FREQ,
                wlen_L1,
                wlen_L7,
            )

        # Galileo: L1/L8 combination (E1/E6)
        if "L1" in sat_obs.signals and "L8" in sat_obs.signals:
            sig_l1 = sat_obs.signals["L1"]
            sig_l8 = sat_obs.signals["L8"]
            ambiguities["L1_L8"] = compute_dual_frequency_ambiguity(
                sig_l1.pseudorange,
                sig_l1.carrier_phase,
                sig_l8.pseudorange,
                sig_l8.carrier_phase,
                L1_FREQ,
                E6_FREQ,
                wlen_L1,
                wlen_L8,
            )

    return ambiguities


def parse_rinex_observation_file(
    file_path: str,
    signal_code_map: dict[str, list[list[str]]],
) -> list[EpochObservations]:
    """
    Parse a RINEX observation file and return a list of EpochObservations.

    Args:
        file_path: Path to the RINEX observation file.
        signal_code_map: Mapping of system name to list of [band_number, signal_code]
            pairs for observation codes like C1C, L1C, C5X, L5X.
    Returns:
        List of EpochObservations containing satellite observations per epoch.
    """
    # Placeholder for actual parsing logic
    epochs = []
    try:
        _data = gr.load(file_path)
    except Exception as e:
        raise RuntimeError(f"Failed to load RINEX file: {e}")
    # Implement parsing logic here to populate epochs
    for time_idx, time_val in enumerate(_data.time.values):
        epoch_obs = EpochObservations(
            datetime=datetime.fromtimestamp(
                time_val.astype("O") / 1e9, tz=timezone.utc
            ).replace(tzinfo=None),
            satellites_gps=[],
            satellites_qzss=[],
            satellites_galileo=[],
            satellites_glonass=[],
        )
        # Iterate over satellites and populate epoch_obs
        sv_values = [str(s) for s in _data.sv.values]
        for sv in sv_values:
            prn = int(sv[1:]) if sv[1:].isdigit() else None
            if prn is None:
                continue
            sat_obs = SatelliteObservation(prn=prn, signals={}, ambiguities={})
            # GPS (G)
            for system_code, system_name in [
                ("G", "GPS"),
                ("J", "QZSS"),
                ("E", "Galileo"),
                ("R", "GLONASS"),
            ]:
                if not sv.startswith(system_code):
                    continue
                if system_name not in signal_code_map:
                    raise KeyError(f"signal_code_map missing system: {system_name}")
                # Extract signal observations (pseudorange, carrier phase, etc.)
                for band_number, signal_code in signal_code_map[system_name]:
                    pr_key = f"C{band_number}{signal_code}"
                    cp_key = f"L{band_number}{signal_code}"
                    dp_key = f"D{band_number}{signal_code}"
                    snr_key = f"S{band_number}{signal_code}"

                    # Check if all required keys exist in the dataset
                    if not all(
                        key in _data for key in [pr_key, cp_key, dp_key, snr_key]
                    ):
                        continue

                    pr = _data[pr_key].sel(sv=sv, time=time_val).values
                    cp = _data[cp_key].sel(sv=sv, time=time_val).values
                    dp = _data[dp_key].sel(sv=sv, time=time_val).values
                    snr = _data[snr_key].sel(sv=sv, time=time_val).values

                    # Skip if any value is NaN or size is 0
                    if pr.size > 0 and cp.size > 0 and dp.size > 0 and snr.size > 0:
                        if not (
                            np.isnan(pr).any()
                            or np.isnan(cp).any()
                            or np.isnan(dp).any()
                            or np.isnan(snr).any()
                        ):
                            signal_obs = SatelliteSignalObservation(
                                pseudorange=float(pr),
                                carrier_phase=float(cp),
                                doppler_=float(dp),
                                snr=float(snr),
                            )
                            # Use band name like L1, L2, L5, L7, L8
                            band_name = f"L{band_number}"
                            sat_obs.add_signal_observation(band_name, signal_obs)
                # Only add satellite observation if it has signals
                if sat_obs.signals:
                    # Compute ambiguities for GPS/QZSS/Galileo
                    if system_name in ["GPS", "QZSS", "Galileo"]:
                        sat_obs.ambiguities = compute_ambiguities_for_satellite(
                            sat_obs, system_name
                        )

                    if system_name == "GPS":
                        epoch_obs.satellites_gps.append(sat_obs)
                    elif system_name == "QZSS":
                        epoch_obs.satellites_qzss.append(sat_obs)
                    elif system_name == "Galileo":
                        epoch_obs.satellites_galileo.append(sat_obs)
                    elif system_name == "GLONASS":
                        epoch_obs.satellites_glonass.append(sat_obs)
            # Similar logic for other constellations (QZSS, Galileo, GLONASS)
        epochs.append(epoch_obs)
    return epochs


def save_gnss_observations_to_json(
    epochs: list[EpochObservations],
    output_file: str,
):
    # Convert to JSON-serializable format
    def convert_to_json_serializable(obj):
        """Convert objects to JSON-serializable format."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: convert_to_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_json_serializable(item) for item in obj]
        elif hasattr(obj, "__dict__"):
            return convert_to_json_serializable(obj.__dict__)
        else:
            return obj

    with open(output_file, "w", encoding="utf-8") as f:
        import json

        output_data = {
            "filename": output_file,
            "epochs": [convert_to_json_serializable(epoch) for epoch in epochs],
        }
        json.dump(output_data, f, indent=2)


# ------------------------------------------------------------


def signal_code_check(rnxobs):
    """
    Check available signal codes in the RINEX observation data.

    Args:
        rnxobs: RINEX observation data
    Returns:
        dict: Dictionary with frequency prefixes as keys and list of available signal codes as values.
              Example: {
                  'G': {
                      'L1': 'C',
                      'L2': 'C',
                      'L5': 'I'
                    },
                    'E': {
                      'L1': 'C',
                      'L5': 'I',
                      'L5A': 'Q'
                      'L5B': 'X'
                    },
                ....
              }
    """
    available_obs = list(rnxobs.data_vars)
    signal_codes = {}

    for obs in available_obs:
        if obs.startswith("L"):
            freq_prefix = obs[:2]  # e.g., 'L1', 'L2', 'L5'
            code = obs[2:]  # e.g., 'C', 'I', 'Q'
            if freq_prefix not in signal_codes:
                signal_codes[freq_prefix] = set()
            signal_codes[freq_prefix].add(code)

    # Convert sets to sorted lists
    for freq in signal_codes:
        signal_codes[freq] = sorted(list(signal_codes[freq]))

    return signal_codes


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
) -> dict[np.datetime64, list[tuple[str, float]]]:
    """
    Sort satellites by signal strength for each epoch.

    Args:
        rnxobs (rinexobs): GNSS observation data
        signal_type (str): Signal strength indicator (default: "S1C")
        constellation (str): Constellation type filter (e.g., "G", "J", "E").
                           None for all constellations.

    Returns:
        dict[np.datetime64, list[tuple[str, float]]]: Dictionary with time as keys and list of (satellite, signal_strength)
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


def get_multifrequency_measurements(rnxobs: rinexobs, constellation_prefix: str = "G"):
    """
    Calculate multifrequency measurements for all satellites in the RINEX observation data.

    Args:
        rnxobs: RINEX observation data (georinex rinexobs object)
        constellation_prefix: Prefix for the constellation to filter (default: 'G' for GPS)
    """
    # Get all satellite list
    sv_values = [str(s) for s in rnxobs.sv.values]
    l1_obs_code, l2_obs_code = None, None

    # Filter GPS satellites only (satellites starting with 'G')
    _satellites = sorted(
        [s for s in sv_values if s.startswith(constellation_prefix)],
        key=lambda x: int(x[1:]) if x[1:].isdigit() else 999,
    )

    # make time ordered output data structure
    out_data = []
    for time_idx, time_val in enumerate(rnxobs.time.values):
        out_data.append({"time": time_val, "visible_satellites": [], "ambiguities": {}})
        if len(out_data) != time_idx + 1:
            raise ValueError("Time index mismatch in output data structure")
        # Check GPS satellites observed at this epoch
        for sv in _satellites:
            if l1_obs_code is None:
                l1_obs_code = get_available_signal_code(rnxobs, sv, "L1")
            if l2_obs_code is None:
                if constellation_prefix == "E":
                    l2_obs_code = get_available_signal_code(rnxobs, sv, "L5")
                elif constellation_prefix in ["G", "J"]:
                    l2_obs_code = get_available_signal_code(rnxobs, sv, "L2")
            if f"S1{l1_obs_code}" in rnxobs:
                strength = float(
                    rnxobs[f"S1{l1_obs_code}"].sel(sv=sv, time=time_val).values
                )
                if np.isnan(strength):
                    continue  # No data for this satellite at this epoch
            out_data[time_idx]["visible_satellites"].append(sv)

    # Calculate ambiguities for each satellite
    for sv in _satellites:
        if constellation_prefix == "E":
            l1_obs_code = get_available_signal_code(rnxobs, sv, "L1")
            l2_obs_code = get_available_signal_code(rnxobs, sv, "L5")
            _wl_amb = get_widelane_ambiguity(
                rnxobs,
                sv,
                f"C1{l1_obs_code}",
                f"L1{l1_obs_code}",
                f"C2{l2_obs_code}",
                f"L5{l2_obs_code}",
            )
            _io_amb = get_ionospheric_ambiguity(
                rnxobs,
                sv,
                f"C1{l1_obs_code}",
                f"L1{l1_obs_code}",
                f"C2{l2_obs_code}",
                f"L5{l2_obs_code}",
            )
        elif constellation_prefix in ["G", "J"]:
            l1_obs_code = get_available_signal_code(rnxobs, sv, "L1")
            l2_obs_code = get_available_signal_code(rnxobs, sv, "L2")
            _wl_amb = get_widelane_ambiguity(
                rnxobs,
                sv,
                f"C1{l1_obs_code}",
                f"L1{l1_obs_code}",
                f"C2{l2_obs_code}",
                f"L2{l2_obs_code}",
            )
            _io_amb = get_ionospheric_ambiguity(
                rnxobs,
                sv,
                f"C1{l1_obs_code}",
                f"L1{l1_obs_code}",
                f"C2{l2_obs_code}",
                f"L2{l2_obs_code}",
            )
        else:
            continue  # Unsupported constellation

        if l1_obs_code is None:
            continue  # No L1 signal available for this satellite
        # calculate wide-lane ambiguity to confirm observation presence
        if _wl_amb.count().values == 0 or _io_amb.count().values == 0:
            continue  # No valid observations for this satellite
        for time_val in _wl_amb.time.values:
            time_idx = np.where(rnxobs.time.values == time_val)[0][0]
            if time_idx is None:
                continue
            if np.isnan(_wl_amb.sel(time=time_val).values) or np.isnan(
                _io_amb.sel(time=time_val).values
            ):
                continue
            if sv not in out_data[time_idx]["ambiguities"]:
                out_data[time_idx]["ambiguities"][sv] = {
                    "widelane_L1L2": None,
                    "ionospheric_L1L2": None,
                    "S1": None,
                    "S2": None,
                }
            out_data[time_idx]["ambiguities"][sv]["widelane_L1L2"] = float(
                _wl_amb.sel(time=time_val).values
            )
            out_data[time_idx]["ambiguities"][sv]["ionospheric_L1L2"] = float(
                _io_amb.sel(time=time_val).values
            )
            # Also store signal strengths
            if f"S1{l1_obs_code}" in rnxobs:
                s1_strength = float(
                    rnxobs[f"S1{l1_obs_code}"].sel(sv=sv, time=time_val).values
                )
                out_data[time_idx]["ambiguities"][sv]["S1"] = s1_strength
            if f"S2{l2_obs_code}" in rnxobs:
                s2_strength = float(
                    rnxobs[f"S2{l2_obs_code}"].sel(sv=sv, time=time_val).values
                )
                out_data[time_idx]["ambiguities"][sv]["S2"] = s2_strength
    return out_data
