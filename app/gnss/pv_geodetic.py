"""Error-state Kalman filter for GNSS position/velocity on geodetic coordinates.

The nominal state is kept outside the filter as geodetic position
(lat, lon, h) and ENU velocity. The Kalman filter estimates only the error
state in the local ENU frame at the nominal position (meters, m/s):

    dp = C_n (r_true - r_nom)            position error, r in ECEF
    dv = C_n v_true^e - v_nom^n          velocity error, v^e true velocity in ECEF

where C_n is the ECEF->ENU rotation at the nominal position. After each
measurement update the error is fed back into the nominal state and reset to
zero (closed-loop error-state filter). The ENU frame moves with the nominal
position, so the error transition and the reset include the frame rotation.

See doc/pv_filter_geodetic.md for the formulation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.gnss.coordinates import ecef_to_enu_matrix, ecef_to_llh, llh_to_ecef, radii_of_curvature
from app.gnss.kalman import CHI2_6DOF_999, KalmanFilter, cv_process_noise

# Finite-difference steps for the numerical error transition matrix
FD_STEP_POS: float = 1.0  # m
FD_STEP_VEL: float = 0.1  # m/s


def wrap_lon(lon_rad: float) -> float:
    """Wrap longitude to [-pi, pi)."""
    return (lon_rad + np.pi) % (2 * np.pi) - np.pi


def _deg(llh_rad: np.ndarray) -> np.ndarray:
    return np.array([np.degrees(llh_rad[0]), np.degrees(llh_rad[1]), llh_rad[2]])


def _rad(llh_deg: np.ndarray) -> np.ndarray:
    return np.array([np.radians(llh_deg[0]), np.radians(llh_deg[1]), llh_deg[2]])


def enu_matrix(llh_rad: np.ndarray) -> np.ndarray:
    """ECEF->ENU rotation at geodetic position [lat_rad, lon_rad, h_m]."""
    return ecef_to_enu_matrix(np.degrees(llh_rad[0]), np.degrees(llh_rad[1]))


def propagate_llh(llh_rad: np.ndarray, vel_enu: np.ndarray, dt: float) -> np.ndarray:
    """
    Propagate geodetic position with constant ENU velocity (midpoint integration).

        lat_dot = vN / (M + h)
        lon_dot = vE / ((N + h) cos(lat))
        h_dot   = vU

    Args:
        llh_rad: [lat_rad, lon_rad, h_m].
        vel_enu: [vE, vN, vU] (m/s).
        dt: Propagation interval (s).
    """
    lat, lon, h = llh_rad
    v_e, v_n, v_u = vel_enu
    M, _ = radii_of_curvature(lat)
    lat_mid = lat + 0.5 * dt * v_n / (M + h)
    h_mid = h + 0.5 * dt * v_u
    M, N = radii_of_curvature(lat_mid)
    return np.array(
        [
            lat + dt * v_n / (M + h_mid),
            wrap_lon(lon + dt * v_e / ((N + h_mid) * np.cos(lat_mid))),
            h + dt * v_u,
        ]
    )


def apply_error(llh_rad: np.ndarray, vel_enu: np.ndarray, dx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Return the state obtained by applying error dx to the nominal state (exact, via ECEF).

        r = r_nom + C_n^T dp
        v^e = C_n^T (v_nom^n + dv),  expressed in ENU at the new position

    Args:
        llh_rad: Nominal [lat_rad, lon_rad, h_m].
        vel_enu: Nominal ENU velocity (m/s).
        dx: Error state [dE, dN, dU, dvE, dvN, dvU] in ENU at the nominal position.

    Returns:
        (llh_rad, vel_enu) of the corrected state; vel_enu is in ENU at the corrected position.
    """
    C_n = enu_matrix(llh_rad)
    llh_new = _rad(ecef_to_llh(llh_to_ecef(_deg(llh_rad)) + C_n.T @ dx[0:3]))
    vel_ecef = C_n.T @ (vel_enu + dx[3:6])
    return llh_new, enu_matrix(llh_new) @ vel_ecef


def error_between(
    llh_nom_rad: np.ndarray,
    vel_nom_enu: np.ndarray,
    llh_rad: np.ndarray,
    vel_enu: np.ndarray,
) -> np.ndarray:
    """Error state of (llh_rad, vel_enu) relative to the nominal state, in ENU at the nominal position.

    Inverse of ``apply_error``. vel_enu is expressed in ENU at llh_rad.
    """
    C_n = enu_matrix(llh_nom_rad)
    dp = C_n @ (llh_to_ecef(_deg(llh_rad)) - llh_to_ecef(_deg(llh_nom_rad)))
    dv = C_n @ enu_matrix(llh_rad).T @ vel_enu - vel_nom_enu
    return np.concatenate([dp, dv])


def error_transition(llh_rad: np.ndarray, vel_enu: np.ndarray, dt: float) -> np.ndarray:
    """
    Error-state transition matrix Phi over dt, by central finite differences.

    Phi maps the error in ENU at the nominal position at t to the error in ENU at
    the propagated nominal position at t + dt. It includes the constant-velocity
    terms (dp += dv dt), the rotation of the ENU frame, and the earth curvature
    (transport rate) couplings. For short dt it is close to [[I, dt I], [0, I]].
    """
    llh_nom = propagate_llh(llh_rad, vel_enu, dt)
    steps = np.array([FD_STEP_POS] * 3 + [FD_STEP_VEL] * 3)
    Phi = np.zeros((6, 6))
    for j in range(6):
        cols = []
        for sign in (1.0, -1.0):
            dx = np.zeros(6)
            dx[j] = sign * steps[j]
            llh_t, vel_t = apply_error(llh_rad, vel_enu, dx)
            cols.append(error_between(llh_nom, vel_enu, propagate_llh(llh_t, vel_t, dt), vel_t))
        Phi[:, j] = (cols[0] - cols[1]) / (2 * steps[j])
    return Phi


@dataclass
class GeodeticPvOutput:
    time: float
    position_llh: np.ndarray  # [lat_deg, lon_deg, h_m]
    velocity_enu: np.ndarray  # [vE, vN, vU] (m/s)
    covariance_enu: np.ndarray  # 6x6 error covariance in ENU at position_llh
    nis: float
    accepted: bool

    @property
    def position_ecef(self) -> np.ndarray:
        return llh_to_ecef(self.position_llh)

    @property
    def velocity_ecef(self) -> np.ndarray:
        C = ecef_to_enu_matrix(self.position_llh[0], self.position_llh[1])
        return C.T @ self.velocity_enu


class GeodeticPvFilter:
    """
    Closed-loop error-state Kalman filter with constant-velocity model.

    Nominal state: geodetic position (lat, lon, h) and ENU velocity.
    Error state:   [dE, dN, dU, dvE, dvN, dvU] in ENU at the nominal position.
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
            accel_psd_vertical: Vertical acceleration PSD (m^2/s^3).
                Keep small for vehicles moving on the earth surface.
            gate: NIS chi-square threshold for outlier rejection (None disables gating).
            max_consecutive_rejects: Reinitialize from the measurement after this many
                consecutive rejections to recover from filter divergence.
        """
        self.accel_psd = np.diag([accel_psd_horizontal, accel_psd_horizontal, accel_psd_vertical])
        self.gate = gate
        self.max_consecutive_rejects = max_consecutive_rejects
        self.llh_rad: np.ndarray | None = None
        self.vel_enu: np.ndarray | None = None
        self.kf: KalmanFilter | None = None
        self.time: float | None = None
        self._num_rejects = 0
        self._H = np.eye(6)

    @staticmethod
    def measurement_cov(
        pos_sigma_enu: float | np.ndarray,
        vel_sigma_enu: float | np.ndarray,
    ) -> np.ndarray:
        """Diagonal ENU measurement covariance from per-axis (or scalar) 1-sigma values."""
        pos_var = np.broadcast_to(np.asarray(pos_sigma_enu, dtype=float) ** 2, (3,))
        vel_var = np.broadcast_to(np.asarray(vel_sigma_enu, dtype=float) ** 2, (3,))
        return np.diag(np.concatenate([pos_var, vel_var]))

    @property
    def position_llh(self) -> np.ndarray:
        """Nominal position [lat_deg, lon_deg, h_m]."""
        if self.llh_rad is None:
            raise RuntimeError("Filter is not initialized")
        return _deg(self.llh_rad)

    def _initialize(self, time: float, pos_ecef: np.ndarray, vel_ecef: np.ndarray, R_enu: np.ndarray) -> None:
        self.llh_rad = _rad(ecef_to_llh(pos_ecef))
        self.vel_enu = enu_matrix(self.llh_rad) @ vel_ecef
        self.kf = KalmanFilter(np.zeros(6), R_enu)
        self.time = time
        self._num_rejects = 0

    def predict(self, time: float) -> None:
        """Propagate the nominal state and the error covariance to the given time (s)."""
        if self.kf is None or self.time is None or self.llh_rad is None or self.vel_enu is None:
            raise RuntimeError("Filter is not initialized")
        dt = time - self.time
        if dt < 0:
            raise ValueError(f"Time went backwards: dt={dt}")
        if dt > 0:
            Phi = error_transition(self.llh_rad, self.vel_enu, dt)
            self.kf.predict(Phi, cv_process_noise(dt, self.accel_psd))
            self.llh_rad = propagate_llh(self.llh_rad, self.vel_enu, dt)
            self.time = time

    def _innovation(self, pos_ecef: np.ndarray, vel_ecef: np.ndarray) -> np.ndarray:
        """Measurement minus nominal, expressed in ENU at the nominal position."""
        assert self.llh_rad is not None and self.vel_enu is not None
        C_n = enu_matrix(self.llh_rad)
        d_pos = C_n @ (pos_ecef - llh_to_ecef(self.position_llh))
        return np.concatenate([d_pos, C_n @ vel_ecef - self.vel_enu])

    def _feedback(self) -> None:
        """Inject the estimated error into the nominal state, rotate P to the new ENU frame and reset."""
        assert self.kf is not None and self.llh_rad is not None and self.vel_enu is not None
        C_old = enu_matrix(self.llh_rad)
        self.llh_rad, self.vel_enu = apply_error(self.llh_rad, self.vel_enu, self.kf.x)
        rot = enu_matrix(self.llh_rad) @ C_old.T
        T = np.block([[rot, np.zeros((3, 3))], [np.zeros((3, 3)), rot]])
        self.kf.P = T @ self.kf.P @ T.T
        self.kf.x = np.zeros(6)

    def step_ecef(
        self,
        time: float,
        position_ecef: np.ndarray,
        velocity_ecef: np.ndarray,
        R_enu: np.ndarray,
    ) -> GeodeticPvOutput:
        """
        Process one GNSS fix given in ECEF (e.g. receiver PVT output).

        Args:
            time: Measurement time (s), e.g. GPS seconds.
            position_ecef: Measured ECEF position (m).
            velocity_ecef: Measured ECEF velocity (m/s).
            R_enu: 6x6 measurement noise covariance in ENU (see ``measurement_cov``).
        """
        pos_ecef = np.asarray(position_ecef, dtype=float)
        vel_ecef = np.asarray(velocity_ecef, dtype=float)
        if self.kf is None:
            self._initialize(time, pos_ecef, vel_ecef, R_enu)
            nis, accepted = 0.0, True
        else:
            self.predict(time)
            z = self._innovation(pos_ecef, vel_ecef)
            result = self.kf.update(z, self._H, R_enu, gate=self.gate)
            nis, accepted = result.nis, result.accepted
            if accepted:
                self._feedback()
                self._num_rejects = 0
            else:
                self._num_rejects += 1
                if self._num_rejects >= self.max_consecutive_rejects:
                    self._initialize(time, pos_ecef, vel_ecef, R_enu)
        assert self.kf is not None and self.vel_enu is not None
        return GeodeticPvOutput(
            time=time,
            position_llh=self.position_llh,
            velocity_enu=self.vel_enu.copy(),
            covariance_enu=self.kf.P.copy(),
            nis=nis,
            accepted=accepted,
        )

    def step(
        self,
        time: float,
        position_llh: np.ndarray,
        velocity_enu: np.ndarray,
        R_enu: np.ndarray,
    ) -> GeodeticPvOutput:
        """
        Process one GNSS fix given in geodetic coordinates.

        Args:
            time: Measurement time (s), e.g. GPS seconds.
            position_llh: Measured [lat_deg, lon_deg, h_m].
            velocity_enu: Measured [vE, vN, vU] (m/s) in ENU at the measured position.
            R_enu: 6x6 measurement noise covariance in ENU (see ``measurement_cov``).
        """
        C_meas = ecef_to_enu_matrix(position_llh[0], position_llh[1])
        return self.step_ecef(time, llh_to_ecef(np.asarray(position_llh, dtype=float)), C_meas.T @ np.asarray(velocity_enu, dtype=float), R_enu)
