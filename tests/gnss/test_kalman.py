import numpy as np
import pytest

from app.gnss.coordinates import ecef_to_enu_matrix
from app.gnss.kalman import KalmanFilter, PvFilter, cv_process_noise, cv_transition

# Tokyo, approx. (lat 35.68, lon 139.76, h 50 m)
ORIGIN_ECEF = np.array([-3959840.0, 3352840.0, 3697600.0])


def make_trajectory(times: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Vehicle driving north-east at 10 m/s with a gentle turn."""
    C = ecef_to_enu_matrix(35.68, 139.76)  # ECEF -> ENU
    pos, vel = [], []
    for t in times:
        heading = 0.01 * t
        v_enu = np.array([10.0 * np.sin(heading), 10.0 * np.cos(heading), 0.0])
        p_enu = np.array([1000.0 * (1 - np.cos(heading)), 1000.0 * np.sin(heading), 0.0])
        pos.append(ORIGIN_ECEF + C.T @ p_enu)
        vel.append(C.T @ v_enu)
    return np.array(pos), np.array(vel)


def run_filter(pf: PvFilter, times, pos_meas, vel_meas, R):
    return [pf.step(t, p, v, R) for t, p, v in zip(times, pos_meas, vel_meas)]


def test_cv_model_matrices():
    dt = 0.5
    F = cv_transition(dt)
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    assert np.allclose(F @ x, [3.0, 4.5, 6.0, 4.0, 5.0, 6.0])

    Q = cv_process_noise(dt, np.eye(3))
    assert np.allclose(Q, Q.T)
    assert np.all(np.linalg.eigvalsh(Q) > 0)


def test_kalman_filter_scalar_update():
    kf = KalmanFilter(np.array([0.0]), np.array([[1.0]]))
    res = kf.update(np.array([2.0]), np.array([[1.0]]), np.array([[1.0]]))
    assert res.accepted
    assert np.isclose(kf.x[0], 1.0)
    assert np.isclose(kf.P[0, 0], 0.5)
    assert np.isclose(res.nis, 2.0)


def test_pv_filter_reduces_noise():
    rng = np.random.default_rng(0)
    times = np.arange(0.0, 300.0, 1.0)
    pos_true, vel_true = make_trajectory(times)
    pos_sigma, vel_sigma = 3.0, 0.1
    pos_meas = pos_true + rng.normal(0.0, pos_sigma, pos_true.shape)
    vel_meas = vel_true + rng.normal(0.0, vel_sigma, vel_true.shape)
    R = PvFilter.measurement_cov(pos_sigma, vel_sigma)

    out = run_filter(PvFilter(accel_psd_horizontal=0.1, accel_psd_vertical=0.01), times, pos_meas, vel_meas, R)
    est = np.array([o.position_ecef for o in out])

    skip = 20  # ignore convergence
    rms_meas = np.sqrt(np.mean(np.sum((pos_meas - pos_true)[skip:] ** 2, axis=1)))
    rms_kf = np.sqrt(np.mean(np.sum((est - pos_true)[skip:] ** 2, axis=1)))
    assert rms_kf < 0.5 * rms_meas
    assert all(o.accepted for o in out)

    # NIS should be consistent with chi-square(6): mean ~ 6
    mean_nis = np.mean([o.nis for o in out[skip:]])
    assert 3.0 < mean_nis < 9.0


def test_pv_filter_rejects_outlier():
    times = np.arange(0.0, 60.0, 1.0)
    pos_true, vel_true = make_trajectory(times)
    pos_meas = pos_true.copy()
    pos_meas[30] += np.array([100.0, 0.0, 0.0])
    R = PvFilter.measurement_cov(3.0, 0.1)

    out = run_filter(PvFilter(), times, pos_meas, vel_true, R)
    assert not out[30].accepted
    assert np.linalg.norm(out[30].position_ecef - pos_true[30]) < 5.0
    assert out[31].accepted


def test_pv_filter_handles_gap_and_reinit():
    times = np.array([0.0, 1.0, 2.0, 30.0, 31.0])
    pos_true, vel_true = make_trajectory(times)
    R = PvFilter.measurement_cov(3.0, 0.1)
    out = run_filter(PvFilter(), times, pos_true, vel_true, R)
    assert all(o.accepted for o in out)
    # covariance grows over the gap before the update
    assert np.all(np.isfinite(out[-1].covariance))

    # persistent jump triggers reinitialization
    pf = PvFilter(max_consecutive_rejects=3)
    jump = np.array([500.0, 0.0, 0.0])
    t = np.arange(0.0, 10.0, 1.0)
    p, v = make_trajectory(t)
    p[5:] += jump
    out = run_filter(pf, t, p, v, R)
    assert [o.accepted for o in out[5:8]] == [False, False, False]
    assert np.allclose(out[7].position_ecef, p[7])
    assert out[8].accepted


def test_pv_filter_rejects_backward_time():
    pf = PvFilter()
    R = PvFilter.measurement_cov(3.0, 0.1)
    pf.step(10.0, ORIGIN_ECEF, np.zeros(3), R)
    with pytest.raises(ValueError):
        pf.step(9.0, ORIGIN_ECEF, np.zeros(3), R)
