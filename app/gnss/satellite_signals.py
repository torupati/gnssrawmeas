from logging import getLogger
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

import georinex as gr

from app.gnss.constants import (
    CLIGHT,
    L1_FREQ,
    L2_FREQ,
    L5_FREQ,
    E5B_FREQ,
    E8_FREQ,
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


@dataclass
class PairedObservation:
    epoch: str
    datetime: datetime
    observation: EpochObservations
    ref_observation: EpochObservations

    @property
    def time_str(self) -> str:
        return self.datetime.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def age_seconds(self) -> float:
        return (self.datetime - self.ref_observation.datetime).total_seconds()


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

    # Galileo: L1/L7(E1/E5B), L1/L8(E1/E5AB) combination
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

        # Galileo: L1/L8 combination (E1/E8)
        if "L1" in sat_obs.signals and "L8" in sat_obs.signals:
            sig_l1 = sat_obs.signals["L1"]
            sig_l8 = sat_obs.signals["L8"]
            ambiguities["L1_L8"] = compute_dual_frequency_ambiguity(
                sig_l1.pseudorange,
                sig_l1.carrier_phase,
                sig_l8.pseudorange,
                sig_l8.carrier_phase,
                L1_FREQ,
                E8_FREQ,
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
