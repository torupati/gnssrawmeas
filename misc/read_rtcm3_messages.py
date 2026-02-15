from __future__ import annotations

from pathlib import Path
import sys

# Add parent directory to path to import from app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.gnss.rtcm3 import read_rtcm3_file, _band_wavelength


def main() -> None:
    rtcm_path = Path(__file__).resolve().parents[1] / "sample_data" / "rtcm3" / "b.rtcm3"
    gps_week_number = 2384

    epochs = read_rtcm3_file(rtcm_path, gps_week_number)

    for buffered_epoch in epochs:
        print(buffered_epoch)
        for sat_list, system_code in [
            (buffered_epoch.satellites_gps, "G"),
            (buffered_epoch.satellites_qzss, "J"),
            (buffered_epoch.satellites_galileo, "E"),
            (buffered_epoch.satellites_glonass, "R"),
        ]:
            for sat in sat_list:
                for sig, obs in sat.signals.items():
                    wavelength = _band_wavelength(sig)
                    expected_cycles = obs.pseudorange / wavelength
                    print(f"{system_code}{sat.prn:02d} {sig}: {obs}")
                    print(f"  wlen={wavelength:.6f}m, exp_cycles={expected_cycles:.1f}, obs_cycles={obs.carrier_phase:.1f}")
        break  # Just print the first epoch for demonstration


if __name__ == "__main__":
    main()
