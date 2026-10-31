import numpy as np
import pytest

from app.gnss.coordinates import ecef_to_enu_matrix, ecef_to_llh, llh_to_ecef
from app.gnss.kalman import PvFilter, cv_transition
from app.gnss.pv_geodetic import GeodeticPvFilter, apply_error, enu_matrix, error_between, error_transition, propagate_llh

ORIGIN_LLH = np.array([35.68, 139.76, 50.0])


def make_surface_trajectory(times: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Vehicle on the ellipsoid surface (constant h) at 10 m/s with a gentle turn.

    Returns geodetic positions [lat_deg, lon_deg, h] and ENU velocities.
    """
    llh = np.array([np.radians(ORIGIN_LLH[0]), np.radians(ORIGIN_LLH[1]), ORIGIN_LLH[2]])
    pos, vel = [], []
    t_prev = times[0]
    for t in times:
        # integrate finely so the truth is accurate
        sub = np.linspace(t_prev, t, 11)
        for t0, t1 in zip(sub[:-1], sub[1:]):
            heading = 0.01 * 0.5 * (t0 + t1)
            llh = propagate_llh(llh, np.array([10.0 * np.sin(heading), 10.0 * np.cos(heading), 0.0]), t1 - t0)
        t_prev = t
        heading = 0.01 * t
        pos.append([np.degrees(llh[0]), np.degrees(llh[1]), llh[2]])
        vel.append([10.0 * np.sin(heading), 10.0 * np.cos(heading), 0.0])
    return np.array(pos), np.array(vel)


def enu_error(llh_est: np.ndarray, llh_true: np.ndarray) -> np.ndarray:
    C = ecef_to_enu_matrix(llh_true[0], llh_true[1])
    return C @ (llh_to_ecef(llh_est) - llh_to_ecef(llh_true))


def add_enu_noise(llh: np.ndarray, d_enu: np.ndarray) -> np.ndarray:
    C = ecef_to_enu_matrix(llh[0], llh[1])
    return ecef_to_llh(llh_to_ecef(llh) + C.T @ d_enu)


def test_llh_ecef_roundtrip():
    for llh in [ORIGIN_LLH, np.array([-33.9, 18.4, 1200.0]), np.array([89.0, -179.9, -30.0])]:
        assert np.allclose(ecef_to_llh(llh_to_ecef(llh)), llh, atol=1e-9)


def test_propagate_matches_enu_displacement():
    llh = np.array([np.radians(ORIGIN_LLH[0]), np.radians(ORIGIN_LLH[1]), ORIGIN_LLH[2]])
    d_enu = np.array([3.0, -4.0, 1.0])
    new = propagate_llh(llh, d_enu, 1.0)
    new_deg = np.array([np.degrees(new[0]), np.degrees(new[1]), new[2]])
    assert np.allclose(enu_error(new_deg, ORIGIN_LLH), d_enu, atol=1e-5)


def test_apply_error_and_error_between_are_inverse():
    llh = np.array([np.radians(ORIGIN_LLH[0]), np.radians(ORIGIN_LLH[1]), ORIGIN_LLH[2]])
    vel = np.array([5.0, -3.0, 0.2])
    dx = np.array([300.0, -400.0, 10.0, 0.5, -0.2, 0.1])
    llh_t, vel_t = apply_error(llh, vel, dx)
    assert np.allclose(error_between(llh, vel, llh_t, vel_t), dx, atol=1e-6)
    # velocity is the same physical vector, expressed in ENU at the new position
    assert np.allclose(enu_matrix(llh_t).T @ vel_t, enu_matrix(llh).T @ (vel + dx[3:6]), atol=1e-9)


def test_error_transition_short_dt_is_constant_velocity():
    llh = np.array([np.radians(ORIGIN_LLH[0]), np.radians(ORIGIN_LLH[1]), ORIGIN_LLH[2]])
    Phi = error_transition(llh, np.array([21.2, 21.2, 0.0]), 1.0)
    assert np.allclose(Phi, cv_transition(1.0), atol=1e-4)


@pytest.mark.parametrize("j", range(6))
def test_error_transition_long_gap_matches_nonlinear_propagation(j):
    """90 km gap: Phi must include ENU frame rotation and curvature couplings."""
    llh = np.array([np.radians(ORIGIN_LLH[0]), np.radians(ORIGIN_LLH[1]), ORIGIN_LLH[2]])
    vel = np.array([21.2, 21.2, 0.0])
    dt = 3000.0
    Phi = error_transition(llh, vel, dt)

    dx = np.zeros(6)
    # 0.01 m/s over 3000 s is a 30 m displacement; residual is second order (d^2 / 2R)
    dx[j] = 10.0 if j < 3 else 0.01
    llh_t, vel_t = apply_error(llh, vel, dx)
    dx1 = error_between(propagate_llh(llh, vel, dt), vel, propagate_llh(llh_t, vel_t, dt), vel_t)
    assert np.allclose(Phi @ dx, dx1, atol=1e-3)

    # frame rotation is significant here: the plain constant-velocity model misses it
    if j < 3:
        assert np.max(np.abs(cv_transition(dt) @ dx - dx1)) > 0.05


def test_feedback_rotates_covariance_to_new_frame():
    pf = GeodeticPvFilter()
    R = GeodeticPvFilter.measurement_cov([1.0, 2.0, 5.0], [0.1, 0.2, 0.3])
    pf.step(0.0, ORIGIN_LLH, np.zeros(3), R)
    assert pf.kf is not None
    pf.kf.x = np.array([50_000.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # large correction to make the rotation visible
    P_before = pf.kf.P.copy()
    llh_before = pf.llh_rad.copy()
    pf._feedback()
    rot = enu_matrix(pf.llh_rad) @ enu_matrix(llh_before).T
    assert np.allclose(pf.kf.P[0:3, 0:3], rot @ P_before[0:3, 0:3] @ rot.T)
    assert not np.allclose(pf.kf.P, P_before)
    assert np.allclose(pf.kf.x, 0.0)


def test_geodetic_filter_reduces_noise():
    rng = np.random.default_rng(1)
    times = np.arange(0.0, 300.0, 1.0)
    pos_true, vel_true = make_surface_trajectory(times)
    pos_sigma = np.array([2.0, 2.0, 5.0])
    vel_sigma = 0.1
    pos_meas = np.array([add_enu_noise(p, rng.normal(0.0, pos_sigma)) for p in pos_true])
    vel_meas = vel_true + rng.normal(0.0, vel_sigma, vel_true.shape)
    R = GeodeticPvFilter.measurement_cov(pos_sigma, vel_sigma)

    pf = GeodeticPvFilter(accel_psd_horizontal=0.1, accel_psd_vertical=0.001)
    out = [pf.step(t, p, v, R) for t, p, v in zip(times, pos_meas, vel_meas)]

    skip = 20
    err_meas = np.array([enu_error(m, t) for m, t in zip(pos_meas, pos_true)])[skip:]
    err_kf = np.array([enu_error(o.position_llh, t) for o, t in zip(out, pos_true)])[skip:]
    for axis in range(3):
        assert np.sqrt(np.mean(err_kf[:, axis] ** 2)) < 0.5 * np.sqrt(np.mean(err_meas[:, axis] ** 2))
    assert all(o.accepted for o in out)
    assert 3.0 < np.mean([o.nis for o in out[skip:]]) < 9.0

    # error covariance is in ENU: vertical position std is larger than horizontal at start
    assert out[0].covariance_enu[2, 2] > out[0].covariance_enu[0, 0]


def test_geodetic_filter_matches_ecef_filter():
    """With the same tuning, the geodetic and ECEF filters should agree closely."""
    rng = np.random.default_rng(2)
    times = np.arange(0.0, 120.0, 1.0)
    pos_true, vel_true = make_surface_trajectory(times)
    pos_ecef = np.array([llh_to_ecef(p) for p in pos_true]) + rng.normal(0.0, 3.0, (len(times), 3))
    vel_ecef = np.array([ecef_to_enu_matrix(p[0], p[1]).T @ v for p, v in zip(pos_true, vel_true)])
    vel_ecef += rng.normal(0.0, 0.1, vel_ecef.shape)

    # isotropic noise so R and Q are the same in ECEF and ENU
    R = PvFilter.measurement_cov(3.0, 0.1)
    ecef_pf = PvFilter(accel_psd_horizontal=0.1, accel_psd_vertical=0.1)
    geo_pf = GeodeticPvFilter(accel_psd_horizontal=0.1, accel_psd_vertical=0.1)
    for t, p, v in zip(times, pos_ecef, vel_ecef):
        o_ecef = ecef_pf.step(t, p, v, R)
        o_geo = geo_pf.step_ecef(t, p, v, R)
        assert np.linalg.norm(o_geo.position_ecef - o_ecef.position_ecef) < 0.05
        assert np.linalg.norm(o_geo.velocity_ecef - o_ecef.velocity_ecef) < 0.01
        assert np.isclose(o_geo.nis, o_ecef.nis, rtol=1e-2, atol=1e-2)


def test_geodetic_filter_rejects_outlier_and_reinit():
    times = np.arange(0.0, 60.0, 1.0)
    pos_true, vel_true = make_surface_trajectory(times)
    pos_meas = pos_true.copy()
    pos_meas[30] = add_enu_noise(pos_true[30], np.array([100.0, 0.0, 0.0]))
    R = GeodeticPvFilter.measurement_cov(3.0, 0.1)

    pf = GeodeticPvFilter()
    out = [pf.step(t, p, v, R) for t, p, v in zip(times, pos_meas, vel_true)]
    assert not out[30].accepted
    assert np.linalg.norm(enu_error(out[30].position_llh, pos_true[30])) < 5.0
    assert out[31].accepted

    # persistent jump triggers reinitialization
    pf = GeodeticPvFilter(max_consecutive_rejects=3)
    jumped = [add_enu_noise(p, np.array([0.0, 500.0, 0.0])) if i >= 5 else p for i, p in enumerate(pos_true[:10])]
    out = [pf.step(t, p, v, R) for t, p, v in zip(times[:10], jumped, vel_true[:10])]
    assert [o.accepted for o in out[5:8]] == [False, False, False]
    assert np.allclose(out[7].position_llh, jumped[7])
    assert out[8].accepted


def test_geodetic_filter_rejects_backward_time():
    pf = GeodeticPvFilter()
    R = GeodeticPvFilter.measurement_cov(3.0, 0.1)
    pf.step(10.0, ORIGIN_LLH, np.zeros(3), R)
    with pytest.raises(ValueError):
        pf.step(9.0, ORIGIN_LLH, np.zeros(3), R)
