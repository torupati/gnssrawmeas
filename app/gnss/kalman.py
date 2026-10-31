"""Kalman filter for GNSS navigation.

Step 1: loosely coupled filter that smooths GNSS position/velocity fixes
(e.g. receiver PVT output or SPP solutions) with a constant-velocity model.

The generic ``KalmanFilter.update`` accepts an externally computed predicted
measurement ``z_pred = h(x)`` and Jacobian ``H``, so the same class can be
reused as an EKF for pseudorange/Doppler measurements later.

State definitions
-----------------
``KalmanFilter`` (generic)
    x : (n,) state vector, P : (n, n) state covariance.
    Time update      x <- F x,  P <- F P F^T + Q
    Measurement      z = h(x) + nu,  nu ~ N(0, R),  H = dh/dx at x

``PvFilter`` (this module, total state in ECEF)
    x = [x, y, z, vx, vy, vz]^T
        x, y, z    : receiver position in ECEF (m)
        vx, vy, vz : receiver velocity in ECEF (m/s)
    P : 6x6 covariance in ECEF (m^2, m^2/s^2)
    Model : constant velocity driven by white acceleration w ~ N(0, S dt),
            S = C_n^e diag(q_h, q_h, q_v) C_e^n  (ENU PSD rotated to ECEF)
        F = [[I, dt I], [0, I]]
        Q = [[dt^3/3 S, dt^2/2 S], [dt^2/2 S, dt S]]
    Measurement : GNSS fix z = [r^e, v^e] (ECEF),  H = I_6

``GeodeticPvFilter`` (app.gnss.pv_geodetic, closed-loop error state)
    Nominal state (outside the filter):
        lat, lon (rad), h (m)  : geodetic position on WGS84
        v^n = [vE, vN, vU]     : velocity in ENU at the nominal position (m/s)
    Error state (Kalman state, reset to zero after each update):
        dx = [dE, dN, dU, dvE, dvN, dvU]^T
        dp = C_e^n (r_true^e - r_nom^e)   position error in ENU (m)
        dv = C_e^n v_true^e - v_nom^n     velocity error in ENU (m/s)
        C_e^n : ECEF->ENU rotation at the nominal position
    P : 6x6 error covariance in ENU at the nominal position
    Model : constant ENU velocity on the ellipsoid; Phi from numerical
            linearization (includes ENU frame rotation), Q with diag(q_h, q_h, q_v)
    Measurement : z = [C_e^n (r_meas^e - r_nom^e), C_e^n v_meas^e - v_nom^n],  H = I_6
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.gnss.coordinates import ecef_to_enu_matrix, ecef_to_llh

# Chi-square 99.9% quantile for 6 degrees of freedom (position + velocity)
CHI2_6DOF_999: float = 22.458


@dataclass
class UpdateResult:
    innovation: np.ndarray
    innovation_cov: np.ndarray
    nis: float
    accepted: bool


class KalmanFilter:
    """Generic (extended) Kalman filter holding state x and covariance P."""

    def __init__(self, x: np.ndarray, P: np.ndarray) -> None:
        self.x = np.asarray(x, dtype=float).copy()
        self.P = np.asarray(P, dtype=float).copy()

    def predict(self, F: np.ndarray, Q: np.ndarray) -> None:
        """Time update: x = F x, P = F P F^T + Q."""
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q
        self.P = 0.5 * (self.P + self.P.T)

    def update(
        self,
        z: np.ndarray,
        H: np.ndarray,
        R: np.ndarray,
        z_pred: np.ndarray | None = None,
        gate: float | None = None,
    ) -> UpdateResult:
        """
        Measurement update.

        Args:
            z: Measurement vector.
            H: Measurement matrix (or Jacobian of h at the current state for EKF).
            R: Measurement noise covariance.
            z_pred: Predicted measurement h(x). Defaults to H @ x (linear KF).
            gate: Chi-square threshold on NIS. If exceeded, the update is skipped.

        Returns:
            UpdateResult with innovation, its covariance, NIS and acceptance flag.
        """
        if z_pred is None:
            z_pred = H @ self.x
        y = z - z_pred
        S = H @ self.P @ H.T + R
        S = 0.5 * (S + S.T)
        nis = float(y @ np.linalg.solve(S, y))
        if gate is not None and nis > gate:
            return UpdateResult(y, S, nis, accepted=False)

        K = np.linalg.solve(S, H @ self.P).T  # K = P H^T S^-1 (S, P symmetric)
        self.x = self.x + K @ y
        # Joseph form keeps P symmetric positive definite
        I_KH = np.eye(self.P.shape[0]) - K @ H
        self.P = I_KH @ self.P @ I_KH.T + K @ R @ K.T
        self.P = 0.5 * (self.P + self.P.T)
        return UpdateResult(y, S, nis, accepted=True)


def cv_transition(dt: float) -> np.ndarray:
    """State transition matrix of the 3D constant-velocity model, state [p(3), v(3)]."""
    F = np.eye(6)
    F[0:3, 3:6] = dt * np.eye(3)
    return F


def cv_process_noise(dt: float, accel_psd_ecef: np.ndarray) -> np.ndarray:
    """
    Discrete process noise of the constant-velocity model driven by white acceleration.

    Args:
        dt: Propagation interval (s).
        accel_psd_ecef: 3x3 acceleration power spectral density in ECEF (m^2/s^3).

    Returns:
        6x6 process noise covariance Q.
    """
    S = accel_psd_ecef
    return np.block(
        [
            [dt**3 / 3.0 * S, dt**2 / 2.0 * S],
            [dt**2 / 2.0 * S, dt * S],
        ]
    )


def enu_psd_to_ecef(pos_ecef: np.ndarray, psd_horizontal: float, psd_vertical: float) -> np.ndarray:
    """Rotate a diagonal ENU acceleration PSD into ECEF at the given position."""
    llh = ecef_to_llh(pos_ecef)
    C = ecef_to_enu_matrix(llh[0], llh[1])  # ECEF -> ENU
    S_enu = np.diag([psd_horizontal, psd_horizontal, psd_vertical])
    return C.T @ S_enu @ C


@dataclass
class PvFilterOutput:
    time: float
    position_ecef: np.ndarray
    velocity_ecef: np.ndarray
    covariance: np.ndarray
    nis: float
    accepted: bool


class PvFilter:
    """
    Constant-velocity Kalman filter for GNSS position/velocity fixes in ECEF.

    State: x = [x, y, z, vx, vy, vz] (m, m/s), receiver position and velocity in ECEF.
    Covariance: P (6x6) in ECEF. See the module docstring for F, Q, H.
    """

    def __init__(
        self,
        accel_psd_horizontal: float = 1.0,
        accel_psd_vertical: float = 0.1,
        gate: float | None = CHI2_6DOF_999,
        max_consecutive_rejects: int = 5,
    ) -> None:
        """
        Args:
            accel_psd_horizontal: Horizontal acceleration PSD (m^2/s^3).
                Roughly 0.01 for static, ~1 for pedestrian/car, larger for agile platforms.
            accel_psd_vertical: Vertical acceleration PSD (m^2/s^3).
            gate: NIS chi-square threshold for outlier rejection (None disables gating).
            max_consecutive_rejects: Reinitialize from the measurement after this many
                consecutive rejections to recover from filter divergence.
        """
        self.accel_psd_horizontal = accel_psd_horizontal
        self.accel_psd_vertical = accel_psd_vertical
        self.gate = gate
        self.max_consecutive_rejects = max_consecutive_rejects
        self.kf: KalmanFilter | None = None
        self.time: float | None = None
        self._num_rejects = 0
        self._H = np.eye(6)

    @staticmethod
    def measurement_cov(pos_sigma: float | np.ndarray, vel_sigma: float | np.ndarray) -> np.ndarray:
        """Diagonal measurement covariance from per-axis (or scalar) 1-sigma values."""
        pos_var = np.broadcast_to(np.asarray(pos_sigma, dtype=float) ** 2, (3,))
        vel_var = np.broadcast_to(np.asarray(vel_sigma, dtype=float) ** 2, (3,))
        return np.diag(np.concatenate([pos_var, vel_var]))

    def _initialize(self, time: float, z: np.ndarray, R: np.ndarray) -> None:
        self.kf = KalmanFilter(z, R)
        self.time = time
        self._num_rejects = 0

    def predict(self, time: float) -> None:
        """Propagate the state to the given time (s)."""
        if self.kf is None or self.time is None:
            raise RuntimeError("Filter is not initialized")
        dt = time - self.time
        if dt < 0:
            raise ValueError(f"Time went backwards: dt={dt}")
        if dt > 0:
            S = enu_psd_to_ecef(self.kf.x[0:3], self.accel_psd_horizontal, self.accel_psd_vertical)
            self.kf.predict(cv_transition(dt), cv_process_noise(dt, S))
            self.time = time

    def step(
        self,
        time: float,
        position_ecef: np.ndarray,
        velocity_ecef: np.ndarray,
        R: np.ndarray,
    ) -> PvFilterOutput:
        """
        Process one GNSS fix.

        Args:
            time: Measurement time (s), e.g. GPS seconds.
            position_ecef: Measured ECEF position (m).
            velocity_ecef: Measured ECEF velocity (m/s).
            R: 6x6 measurement noise covariance (see ``measurement_cov``).
        """
        z = np.concatenate([np.asarray(position_ecef, dtype=float), np.asarray(velocity_ecef, dtype=float)])
        if self.kf is None:
            self._initialize(time, z, R)
            nis, accepted = 0.0, True
        else:
            self.predict(time)
            result = self.kf.update(z, self._H, R, gate=self.gate)
            nis, accepted = result.nis, result.accepted
            if accepted:
                self._num_rejects = 0
            else:
                self._num_rejects += 1
                if self._num_rejects >= self.max_consecutive_rejects:
                    self._initialize(time, z, R)
        assert self.kf is not None
        return PvFilterOutput(
            time=time,
            position_ecef=self.kf.x[0:3].copy(),
            velocity_ecef=self.kf.x[3:6].copy(),
            covariance=self.kf.P.copy(),
            nis=nis,
            accepted=accepted,
        )
