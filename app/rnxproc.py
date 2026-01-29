from dataclasses import dataclass
from datetime import datetime, timezone
import warnings

import numpy as np
import georinex as gr

# Suppress FutureWarnings from xarray/georinex
warnings.filterwarnings("ignore", category=FutureWarning, module="georinex")
warnings.filterwarnings("ignore", category=FutureWarning, module="xarray")


@dataclass
class SatelliteSignalObservation:
    pseudorange: float
    carrier_phase: float
    doppler_: float
    snr: float


@dataclass
class SatelliteObservation:
    prn: int
    signals: dict  # key: band (str), value: SatelliteSignalObservation

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
signal_code_map = {
    "GPS": {
        "1": "C",
        "2": "X",
        "5": "X",
    },
    "GLONASS": {
        "1": "C",
        "2": "C",
    },
    "Galileo": {
        "1": "X",
        "5": "X",
        "7": "X",
        "8": "X",
    },
    "QZSS": {
        "1": "C",
        "2": "X",
        "5": "X",
    },
}


def parse_rinex_observation_file(file_path: str) -> list[EpochObservations]:
    """
    Parse a RINEX observation file and return a list of EpochObservations.

    Args:
        file_path: Path to the RINEX observation file.
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
            sat_obs = SatelliteObservation(prn=prn, signals={})
            # GPS (G)
            for system_code, system_name in [
                ("G", "GPS"),
                ("J", "QZSS"),
                ("E", "Galileo"),
                ("R", "GLONASS"),
            ]:
                if not sv.startswith(system_code):
                    continue
                # Extract signal observations (pseudorange, carrier phase, etc.)
                # Placeholder values; replace with actual extraction logic
                for band_name, signal_code in signal_code_map[system_name].items():
                    pr_key = f"C{band_name}{signal_code}"
                    cp_key = f"L{band_name}{signal_code}"
                    dp_key = f"D{band_name}{signal_code}"
                    snr_key = f"S{band_name}{signal_code}"

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
                            sat_obs.add_signal_observation(band_name, signal_obs)
                # Only add satellite observation if it has signals
                if sat_obs.signals:
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


def test_parse_rinex_observation_file():
    file_path = "sample_data/static_baseline/3075358x.25o"
    epochs = parse_rinex_observation_file(file_path)
    assert len(epochs) > 0, "No epochs parsed from the RINEX file."
    for epoch in epochs:
        assert isinstance(epoch.datetime, datetime), (
            "Epoch datetime is not a datetime object."
        )
        assert len(epoch.satellites_gps) > 0, (
            "No GPS satellite observations for the epoch."
        )
        for sat_obs in epoch.satellites_gps:
            assert isinstance(sat_obs.prn, int), "Satellite PRN is not an integer."
            assert isinstance(sat_obs.signals, dict), (
                "Satellite signals is not a dictionary."
            )

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

    with open("test_output.json", "w") as f:
        import json

        output_data = {
            "filename": file_path,
            "epochs": [convert_to_json_serializable(epoch) for epoch in epochs],
        }
        json.dump(output_data, f, indent=2)


if __name__ == "__main__":
    print("Running RINEX observation file parsing test...")
    test_parse_rinex_observation_file()
    print("RINEX observation file parsing test passed.")
