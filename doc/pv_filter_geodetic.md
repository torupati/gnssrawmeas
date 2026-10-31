# PV Kalman Filter on Geodetic Coordinates

This note describes the position/velocity (PV) Kalman filter implemented in
`app/gnss/pv_geodetic.py` (`GeodeticPvFilter`). It smooths GNSS fixes
(receiver PVT output or SPP solutions) with a constant-velocity model, while
keeping the position in geodetic coordinates (latitude, longitude, height) and
the velocity and uncertainty in a local ENU frame.

The same structure is intended to be extended to raw measurements
(pseudorange, Doppler, carrier phase), where the line-of-sight vector in ENU is
directly given by satellite azimuth and elevation.

An ECEF version of the same model is in `app/gnss/kalman.py` (`PvFilter`). Both
give the same result up to numerical precision (see
`tests/gnss/test_pv_geodetic.py::test_geodetic_filter_matches_ecef_filter`).

## Why not put latitude/longitude directly in the state vector?

Putting $(\varphi, \lambda, h)$ directly into the Kalman state causes problems:

- Mixed units: 1 m corresponds to about $1.6\times10^{-7}$ rad of latitude, so
  the covariance matrix mixes elements of order $10^{-14}$ and $1$ and is badly
  conditioned.
- The longitude rate $\dot\lambda = v_E / ((N+h)\cos\varphi)$ is singular at the poles,
  and the longitude wraps at $\pm 180^\circ$.
- Process and measurement noise are naturally specified in meters
  (horizontal / vertical), not radians.

Therefore an **error-state (indirect) Kalman filter** is used:

| | Variables | Where |
|---|---|---|
| Nominal state | $\varphi, \lambda, h$ (geodetic), $\mathbf{v}^n = [v_E, v_N, v_U]^T$ | kept outside the filter |
| Error state | $\delta\mathbf{x} = [\delta E, \delta N, \delta U, \delta v_E, \delta v_N, \delta v_U]^T$ | Kalman filter, meters and m/s |

The error state is defined exactly, through ECEF, in the ENU frame at the
nominal position:

$$
\delta\mathbf{p}^n = C_e^n \left( \mathbf{r}^e_{true} - \mathbf{r}^e_{nom} \right), \qquad
\delta\mathbf{v}^n = C_e^n \mathbf{v}^e_{true} - \mathbf{v}^n_{nom}
$$

where $C_e^n$ is the ECEF-to-ENU rotation at the nominal position (defined
below). The position error is a straight vector in the local tangent frame; the
velocity error compares the true velocity vector and the nominal velocity
expressed in the same (nominal) ENU frame. The inverse,
"apply error $\delta\mathbf{x}$ to the nominal state", is (`apply_error`)

$$
\mathbf{r}^e = \mathbf{r}^e_{nom} + C_n^e\, \delta\mathbf{p}^n, \qquad
\mathbf{v}^e = C_n^e \left(\mathbf{v}^n_{nom} + \delta\mathbf{v}^n\right)
$$

followed by conversion of $\mathbf{r}^e$ to $(\varphi, \lambda, h)$ and of $\mathbf{v}^e$ to
ENU at the new position. `error_between` computes $\delta\mathbf{x}$ from two states.

The covariance $P$ is therefore the error covariance **in the ENU frame at the
current nominal position**. Since the nominal position moves, this frame moves
too; the covariance is carried from frame to frame in the prediction (through
$\Phi$) and in the reset (through $T$), as described below.

After each measurement update the estimated error is fed back into the nominal
state and the error state is reset to zero (**closed-loop** error-state filter).
Because the error state is always zero after the reset, it stays small and the
linearization is accurate.

## Earth model

WGS84 ellipsoid with semi-major axis $a$ and eccentricity squared $e^2$.
The meridian radius $M$ and prime vertical radius $N$ at latitude $\varphi$ are

$$
M = \frac{a(1-e^2)}{(1-e^2\sin^2\varphi)^{3/2}}, \qquad
N = \frac{a}{\sqrt{1-e^2\sin^2\varphi}}
$$

(`radii_of_curvature` in `app/gnss/coordinates.py`).

Geodetic to ECEF (`llh_to_ecef`):

$$
\mathbf{r}^e =
\begin{bmatrix}
(N+h)\cos\varphi\cos\lambda \\
(N+h)\cos\varphi\sin\lambda \\
(N(1-e^2)+h)\sin\varphi
\end{bmatrix}
$$

The rotation from ECEF to the local ENU frame at $(\varphi, \lambda)$
(`ecef_to_enu_matrix`) is

$$
C_e^n =
\begin{bmatrix}
-\sin\lambda & \cos\lambda & 0 \\
-\sin\varphi\cos\lambda & -\sin\varphi\sin\lambda & \cos\varphi \\
\cos\varphi\cos\lambda & \cos\varphi\sin\lambda & \sin\varphi
\end{bmatrix}
$$

## Motion model

Constant velocity in the local ENU frame, driven by white acceleration noise
$\mathbf{w}(t)$ with power spectral density (PSD)

$$
S = \mathrm{diag}(q_h, q_h, q_v) \quad [\mathrm{m^2/s^3}]
$$

Separate horizontal and vertical PSDs suit vehicles that mostly move on the earth
surface: a small $q_v$ means height changes slowly, which also stabilizes the
horizontal solution when satellite geometry is poor.

### Nominal state propagation

Geodetic kinematics:

$$
\dot\varphi = \frac{v_N}{M+h}, \qquad
\dot\lambda = \frac{v_E}{(N+h)\cos\varphi}, \qquad
\dot h = v_U, \qquad
\dot{\mathbf{v}}^n = 0
$$

They are integrated with the midpoint rule over $\Delta t$ (`propagate_llh`):

$$
\varphi_{1/2} = \varphi + \frac{\Delta t}{2}\frac{v_N}{M(\varphi)+h}, \quad
h_{1/2} = h + \frac{\Delta t}{2} v_U
$$

$$
\varphi^+ = \varphi + \Delta t \frac{v_N}{M(\varphi_{1/2}) + h_{1/2}}, \quad
\lambda^+ = \lambda + \Delta t \frac{v_E}{(N(\varphi_{1/2}) + h_{1/2})\cos\varphi_{1/2}}, \quad
h^+ = h + \Delta t\, v_U
$$

Velocity components in ENU are kept constant, so the velocity vector turns with
the local frame and the trajectory follows the ellipsoid surface (a rhumb line at
constant height). This is the appropriate model for vehicles moving on the earth.
A constant ECEF velocity would instead be a straight line that leaves the surface
(height error $d^2/2R$ for a distance $d$).

The midpoint rule is a second order integrator; for 30 m/s its error against a
finely integrated reference is below $10^{-5}$ m for $\Delta t$ up to 60 s.

### Error transition and covariance propagation

For short $\Delta t$ the error follows the constant-velocity model

$$
F = \begin{bmatrix} I_3 & \Delta t\, I_3 \\ 0 & I_3 \end{bmatrix}
$$

but the ENU frame at the end of the interval is rotated relative to the frame at
the start by about $d/R$ ($d$: distance travelled), and the curvature of the earth
couples the errors (transport-rate terms of order $v\,\delta p / R$). In particular:

- A **position error** (with zero velocity error) is a vector between two points
  that move together along the surface. Expressed in the moving ENU frame it is
  rotated by $C_e^{n}(t+\Delta t)\, C_n^{e}(t)$.
- A **velocity error** is carried with the frame (ENU components constant), up to
  couplings of order $v\,\delta p/R$.

So neither "no rotation" nor "rotate all of $P$" is exact. The filter computes the
exact first-order transition $\Phi$ numerically (`error_transition`): for each
error component $j$, the nominal state is perturbed by $\pm\epsilon_j$ with
`apply_error`, both perturbed states and the nominal state are propagated with
`propagate_llh`, and the resulting error is evaluated with `error_between` in the
ENU frame of the propagated nominal position:

$$
\Phi_{:,j} = \frac{\delta\mathbf{x}(t+\Delta t;\, +\epsilon_j) - \delta\mathbf{x}(t+\Delta t;\, -\epsilon_j)}{2\epsilon_j},
\qquad \epsilon = (1\,\mathrm{m}, 0.1\,\mathrm{m/s})
$$

Central differences cancel the second-order terms. For $\Delta t = 1$ s, $\Phi$
equals $F$ within $10^{-4}$; for a 90 km gap (3000 s at 30 m/s) the frame rotation
changes the propagated position error by about 1% (0.1 m for 10 m), and $\Phi$
reproduces the nonlinear propagation to the second-order residual $d^2/2R$.

The covariance is propagated as

$$
P^- = \Phi P^+ \Phi^T + Q, \qquad
Q = \begin{bmatrix} \frac{\Delta t^3}{3} S & \frac{\Delta t^2}{2} S \\ \frac{\Delta t^2}{2} S & \Delta t\, S \end{bmatrix}
$$

The error state itself remains zero ($\delta\mathbf{x}^- = \Phi \cdot 0 = 0$).
Because $S$ is defined in ENU, no rotation of $Q$ to ECEF is needed (in the ECEF
filter, $S$ must be rotated as $C_n^e S\, C_e^n$). $Q$ is applied in the ENU frame
at the end of the interval; its rotation within one interval is neglected.

## Measurement update

A GNSS fix gives position $\tilde{\mathbf{r}}^e$ and velocity $\tilde{\mathbf{v}}^e$
in ECEF (`step_ecef`), or $(\tilde\varphi, \tilde\lambda, \tilde h)$ and ENU velocity
at the measured position (`step`, converted to ECEF). The measurement of the
error state follows the error definition, in the ENU frame at the nominal position:

$$
\mathbf{z} =
\begin{bmatrix}
C_e^n \left( \tilde{\mathbf{r}}^e - \mathbf{r}^e(\varphi, \lambda, h) \right) \\
C_e^n\, \tilde{\mathbf{v}}^e - \mathbf{v}^n
\end{bmatrix}
= H\,\delta\mathbf{x} + \boldsymbol{\nu}, \qquad H = I_6
$$

The differences are taken through ECEF so they are exact, not only first order
in the geodetic differences. The measured velocity is re-expressed in the
nominal ENU frame before differencing. Measurement noise $R$ is given in ENU, so horizontal and
vertical accuracy reported by a receiver can be used directly.

The standard Kalman update is applied to the error state (prior $\delta\mathbf{x}^- = 0$):

$$
S_k = H P^- H^T + R, \qquad K = P^- H^T S_k^{-1}
$$

$$
\delta\mathbf{x}^+ = K \mathbf{z}, \qquad
P^+ = (I - KH) P^- (I - KH)^T + K R K^T
$$

The Joseph form of the covariance update keeps $P$ symmetric positive definite.

### Outlier gating

The normalized innovation squared (NIS)

$$
\epsilon = \mathbf{z}^T S_k^{-1} \mathbf{z}
$$

follows a $\chi^2$ distribution with 6 degrees of freedom when the filter is
consistent. If $\epsilon$ exceeds the 99.9% quantile (22.458), the measurement is
rejected and only the prediction is kept. After `max_consecutive_rejects`
rejections in a row the filter is reinitialized from the measurement, to recover
from divergence or a real position jump.

The mean NIS is also a tuning check: it should be close to 6. A larger value
means $Q$ or $R$ is too small; a smaller value means they are too large.

## Feedback (closed-loop reset)

The estimated error is injected into the nominal state exactly, through ECEF
(`apply_error`):

$$
\mathbf{r}^e_{nom} \leftarrow \mathbf{r}^e_{nom} + C_n^e\, \delta\hat{\mathbf{p}}^n, \qquad
\mathbf{v}^e_{nom} \leftarrow C_n^e \left(\mathbf{v}^n_{nom} + \delta\hat{\mathbf{v}}^n\right)
$$

then $\mathbf{r}^e_{nom}$ is converted back to $(\varphi', \lambda', h')$ and the velocity
is expressed in ENU at the new position. To first order, the closed-form update

$$
\varphi' = \varphi + \frac{\delta N}{M+h}, \quad
\lambda' = \lambda + \frac{\delta E}{(N+h)\cos\varphi}, \quad
h' = h + \delta U
$$

is the same (difference $\approx \delta p^2 / 2R$, e.g. $8\times10^{-6}$ m for a 10 m
correction), but the ECEF form is the exact inverse of the error definition.

The true state does not move in the reset, but the reference frame does: the ENU
frame at the new nominal position is rotated relative to the old one by
$T_3 = C_e^{n'} C_n^{e}$. The remaining error $\delta\mathbf{x} - \delta\hat{\mathbf{x}}$, and
hence its covariance, is re-expressed in the new frame:

$$
T = \begin{bmatrix} T_3 & 0 \\ 0 & T_3 \end{bmatrix}, \qquad
P^+ \leftarrow T P^+ T^T, \qquad \delta\mathbf{x} \leftarrow 0
$$

The rotation angle is about $|\delta\hat{\mathbf{p}}| / R$ (1.6e-7 rad for 1 m), so it is
tiny for normal corrections but keeps the filter consistent for large ones.

## Summary of one epoch

1. Compute the error transition $\Phi$ over $\Delta t$ (`error_transition`).
2. Propagate the error covariance $P^- = \Phi P \Phi^T + Q$.
3. Propagate the nominal geodetic position with ENU velocity (`propagate_llh`).
4. Form the innovation $\mathbf{z}$ from the GNSS fix in the nominal ENU frame.
5. Check NIS against the $\chi^2$ gate.
6. Update $\delta\mathbf{x}$ and $P$.
7. Apply $\delta\mathbf{x}$ to $(\varphi, \lambda, h, \mathbf{v}^n)$ through ECEF, rotate $P$ to the new ENU frame and reset $\delta\mathbf{x} = 0$.

## Tuning guide

| Parameter | Meaning | Typical value |
|---|---|---|
| `accel_psd_horizontal` $q_h$ | horizontal acceleration PSD | 0.01 (static), 0.1–1 (pedestrian, car), >10 (agile) $\mathrm{m^2/s^3}$ |
| `accel_psd_vertical` $q_v$ | vertical acceleration PSD | 0.001–0.1 for ground vehicles |
| `R_enu` | fix accuracy (1 sigma) | SPP: 2–5 m horizontal, 5–10 m vertical; Doppler velocity 0.05–0.2 m/s |

## Usage

```python
from app.gnss.pv_geodetic import GeodeticPvFilter

pf = GeodeticPvFilter(accel_psd_horizontal=0.5, accel_psd_vertical=0.01)
R = GeodeticPvFilter.measurement_cov(pos_sigma_enu=[2.0, 2.0, 5.0], vel_sigma_enu=0.1)

for t, llh, v_enu in fixes:  # llh = [lat_deg, lon_deg, h_m]
    out = pf.step(t, llh, v_enu, R)
    print(out.position_llh, out.velocity_enu, out.covariance_enu.diagonal() ** 0.5, out.nis)

# ECEF input (e.g. receiver PVT)
out = pf.step_ecef(t, pos_ecef, vel_ecef, R)
```

## Next step: raw measurements

The error state is extended with receiver clock bias $c\,\delta t$ and drift
$c\,\dot{\delta t}$ (and inter-system biases). With the line-of-sight unit vector
in ENU from azimuth $\alpha$ and elevation $\theta$,

$$
\mathbf{e}^n = [\cos\theta\sin\alpha,\ \cos\theta\cos\alpha,\ \sin\theta]^T
$$

the measurement Jacobians become

| Measurement | w.r.t. $\delta\mathbf{p}^n$ | w.r.t. $\delta\mathbf{v}^n$ | clock |
|---|---|---|---|
| Pseudorange $\rho$ | $-\mathbf{e}^{nT}$ | $0$ | $1$ (bias) |
| Doppler range rate $\dot\rho$ | $0$ | $-\mathbf{e}^{nT}$ | $1$ (drift) |
| Carrier phase $\lambda\phi$ | $-\mathbf{e}^{nT}$ | $0$ | $1$ (bias) + ambiguity state |

The predicted measurement $h(\mathbf{x})$ is still computed in ECEF (satellite
position, Earth rotation correction, geometric range), using
$\mathbf{r}^e(\varphi, \lambda, h)$ of the nominal state.
