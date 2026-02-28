# Code-Carrier Smoothing

Carrier smoothing blends code (pseudorange) and carrier phase to reduce
short-term code noise while keeping absolute range. The usual approach is the
Hatch filter (a first-order recursive smoother). It assumes no cycle slip and
constant ambiguity over the smoothing interval.

## Basic Observables

Let $P_k$ be the code pseudorange at epoch $k$ (meters). Let $\phi_k$ be the
carrier phase in cycles and $\lambda$ the carrier wavelength (meters). The
carrier phase range is $L_k = \lambda \phi_k$.

## Kalman Filter of Code-Carrier Smoothing

Define the smoothed code $\tilde{P}_k$ which should be estimated as Maximum a posteriori probability estimator.

$$
	\hat{P}_k = \argmax P(P_k|P_1,\cdots,P_{k-1})
$$

Prediction:

$$
\hat{P}_k^+ = P_{k-1} + (L_k - L_{k-1})
$$

therefore, variance $\sigma^2_k=E[(P_k - E(P_k))^2]$ should be

$$
\sigma_k^2 = \sigma_{k-1}^2 + 2\nu^2
$$

Here noise of carrier phase $\nu$ is regarded as a process noise of Kalman filter. This corresponds to prediction step of Kalman filter.

If we write noise of pseudorange by $\xi$, the posteriori

$$
   \hat{P}_k^+ = \argmax_{P_k} P(P_k|P_k^-)P(P_k^-)
$$

can be calculated. The mean and variance should be

$$
  P_k^+ \leftarrow P_k^- + \frac{(\sigma_k^-)^2}{(\sigma_k^-)^2+\xi^2} (P_k - P_k^-)
$$

and

$$
  (\sigma_k^+)^2 \leftarrow (\sigma^-_k)^2 \left(1 - \frac{(\sigma_k^-)^2}{(\sigma_k^-)^2+\xi^2} \right)
$$


## Cycle Slip Handling

Carrier smoothing is invalid across a cycle slip. When a slip is detected for a
satellite-signal pair, reset the filter for that pair:

- Set $\tilde{P}_k = P_k$ at the slip epoch.
- Restart $N_k$ growth from 1.

Typical slip indicators: loss-of-lock flags, large phase-minus-code residual,
or sudden jumps in $\Delta L_k$.

## Practical Notes

- Choose $N$ based on dynamics and desired noise reduction. Common values are
	50 to 200 epochs for 1 Hz data.
- Longer windows reduce code noise more but react slower to real range changes.
- Apply smoothing per satellite and per signal (e.g., L1, L2).
- Smoothing should be done after basic data edits (outlier removal, slips).
