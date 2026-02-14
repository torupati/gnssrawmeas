from dataclasses import dataclass
from datetime import datetime
from app.gnss.satellite_signals import (
    EpochObservations,
)


@dataclass
class MeasurementForCarrierSmoothing:
    datetime: datetime
    PR: float
    CP: float


def smooth_code_carrier(
    rows_sorted: list[MeasurementForCarrierSmoothing],
    wavelength_m: float,
    code_noise_m: float = 1.0,
    carrier_noise_m: float = 0.02,
    slip_threshold_m: float = 10.0,
) -> list[MeasurementForCarrierSmoothing]:
    """Smooth code and carrier phase measurements using a Kalman filter.

    Args:
            rows (list[MeasurementForCarrierSmoothing]): List of measurement objects.
            wavelength_m (float): Wavelength of the carrier signal in meters.
            code_noise_m (float, optional): Standard deviation of code noise in meters. Defaults to 1.0.
            carrier_noise_m (float, optional): Standard deviation of carrier phase noise in meters. Defaults to 0.02.
            slip_threshold_m (float, optional): Threshold for detecting cycle slips in meters. Defaults to 10.0.

    Returns:
            list[MeasurementForCarrierSmoothing]: List of measurement objects with smoothed measurements.
    """
    smoothed_rows: list[MeasurementForCarrierSmoothing] = []

    pr_prev, pr_var = None, 1000.0
    cp_prev = None
    for meas in rows_sorted:
        # print(row)
        pr = meas.PR
        cp = wavelength_m * meas.CP
        # print(f"Raw P: {pr:.3f}, L: {cp:.3f} {pr - wavelength_m * cp:.3f}")
        if pr_prev is None or cp_prev is None:
            pr_prev, cp_prev = pr, cp
            smoothed_rows.append(
                MeasurementForCarrierSmoothing(
                    datetime=meas.datetime,
                    PR=pr,
                    CP=cp,
                )
            )
            continue

        if pr_prev is not None and cp_prev is not None:
            pr_predicted = pr_prev + (cp - cp_prev)
            pr_var = pr_var + 2 * carrier_noise_m**2
            if abs(pr - pr_predicted) > slip_threshold_m:
                print(
                    f"Large prediction error: {pr - pr_predicted:.3f} m, skipping update"
                )
                pr_prev, pr_var, cp_prev = pr, 1000.0, cp
                smoothed_rows.append(
                    MeasurementForCarrierSmoothing(
                        datetime=meas.datetime,
                        PR=pr,
                        CP=cp,
                    )
                )
                continue
            k_gain = pr_var / (pr_var + code_noise_m**2)
            pr_posteriori = pr_predicted + k_gain * (pr - pr_predicted)
            pr_var_posteriori = (1 - k_gain) * pr_var
            # print(
            #    f"{pr_var=:.3f}, {k_gain:.3f}, {pr_predicted:.3f}, {pr_posteriori:.3f}"
            # )
            # update state
            pr_prev, pr_var, cp_prev = pr_posteriori, pr_var_posteriori, cp
            smoothed_rows.append(
                MeasurementForCarrierSmoothing(
                    datetime=meas.datetime,
                    PR=pr_posteriori,
                    CP=cp,
                )
            )
    return smoothed_rows


def carrier_phase_smoothing(
    epoch_observations: list[EpochObservations],
    smoothing_window: int = 10,
) -> None:
    """Apply carrier phase smoothing to pseudorange measurements in paired observations.

    Args:
            epoch_observations: List of `EpochObservations` containing epoch and reference observations.
            smoothing_window: The window size for smoothing (in number of epochs).
    """
    for epoch_obs in epoch_observations:
        pass
