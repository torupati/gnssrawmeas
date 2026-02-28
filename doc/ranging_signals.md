# Ranging Signals

## Pseudorange Observation Equation

Pseudorange is the distance calculated by multiplying the signal propagation time from a satellite to a receiver by the speed of light.

$$P_r^s = \rho_r^s + c(dt_r - dt^s) + T_r^s + I_r^s + e_P$$

### Variable Definitions

- $P_r^s$ : Pseudorange measured by receiver $r$ from satellite $s$ (m)
- $\rho_r^s$ : Geometric distance between receiver and satellite (m)
- $c$ : Speed of light ($3 \times 10^8$ m/s)
- $dt_r$ : Receiver clock offset (s)
- $dt^s$ : Satellite clock offset (s)
- $T_r^s$ : Tropospheric delay (m)
- $I_r^s$ : Ionospheric delay (m)
- $e_P$ : Pseudorange measurement noise and multipath error (m)

### Alternative Form Using Satellite Transmission Time

The receiver measures the signal reception time $T_r$ on its own clock and extracts the satellite transmission time $T^s$ from the navigation message. The following equation relates these observed times:

$$T^s = T_r - \frac{1}{c}\left(\rho_r^s + T_r^s + I_r^s + e_r^s\right) + (dt^s - dt_r)$$

where:

- $T_r$ : Signal reception time on receiver clock (s)
- $T^s$ : Signal transmission time on satellite clock (s) - extracted from navigation message

Pseudorange is computed from the time difference:

$$P_r^s = c(T_r - T^s) = \rho_r^s + c(dt_r - dt^s) + T_r^s + I_r^s + e_r^s$$

This form emphasizes that pseudorange measurement is fundamentally the receiver observing when the signal arrives and when it was transmitted.


## Carrier Phase Observation Equation

Carrier phase is the phase of the satellite signal's carrier wave observed by the receiver.

$$\Phi_r^s = \frac{1}{\lambda} \rho_r^s + \frac{c}{\lambda}(dt_r - dt^s) - \frac{1}{\lambda}T_r^s + \frac{1}{\lambda}I_r^s + N_r^s + e_\Phi $$

or

$$
L^r_s = \rho_r^s + c(dt_r - dt^s) + T_r^s - I_r^s + \lambda N_r^s + \epsilon_L
$$

### Variable Definitions

- $\Phi_r^s$ : Carrier phase measured by receiver $r$ from satellite $s$ (cycles)
- $L$: Accumulated delta range (meter)
- $\lambda$ : Wavelength of the carrier signal (m)
- $\rho_r^s$ : Geometric distance between receiver and satellite (m)
- $c$ : Speed of light ($3 \times 10^8$ m/s)
- $dt_r$ : Receiver clock offset (s)
- $dt^s$ : Satellite clock offset (s)
- $T_r^s$ : Tropospheric delay (m)
- $I_r^s$ : Ionospheric delay (m) - opposite sign compared to pseudorange
- $N_r^s$ : Ambiguity (integer cycle ambiguity) (cycles)
- $e_r^s$ : Carrier phase measurement noise and multipath error (cycles)

### Relationship between Pseudorange and Carrier Phase

- Pseudorange has low accuracy but increases monotonically
- Carrier phase has high accuracy but contains integer cycle ambiguity
- Ionospheric delay has opposite sign (delays pseudorange, advances carrier phase)

## Ranging Signals

We have 2 ranging signals:

$$
\begin{aligned}
P &= \rho + c(dt_r - dt^s) + T + I + e_P \\
L &= \rho + c(dt_r - dt^s) + T - I + \lambda N_r^s + \epsilon_L
\end{aligned}
$$

- $\lambda$ : Wavelength of the carrier signal (m)
- $\rho$ : Geometric distance between receiver and satellite (m)
- $c$ : Speed of light ($3 \times 10^8$ m/s)
- $dt_r$ : Receiver clock offset (s)
- $dt^s$ : Satellite clock offset (s)
- $T$ : Tropospheric delay (m)
- $I$ : Ionospheric delay (m) - opposite sign compared to pseudorange
- $N$ : Ambiguity (integer cycle ambiguity) (cycles)
- $e_P$ : Pseudorange measurement noise and multipath error (m)
- $e_L$ : Carrier phase measurement noise and multipath error (cycles)
