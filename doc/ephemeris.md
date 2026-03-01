# Ephemeris

## RINEX Navigation Format (RINEX 3.02)

### Example GPS Navigation Record

```
G10 2025 12 24 00 00 00-5.765147507191D-04-3.637978807092D-12 0.000000000000D+00
     9.000000000000D+00-5.968750000000D+00 3.972665477463D-09-1.234327286869D+00
    -2.924352884293D-07 1.094881631434D-02 1.903623342514D-06 5.153646812439D+03
     2.592000000000D+05 2.719461917877D-07-9.103512747561D-01 1.192092895508D-07
     9.919594166456D-01 3.584687500000D+02-2.277835439618D+00-8.024619971918D-09
    -1.082187934614D-10 1.000000000000D+00 2.398000000000D+03 0.000000000000D+00
     2.000000000000D+00 0.000000000000D+00 2.328306436539D-09 9.000000000000D+00
     2.591700000000D+05 4.000000000000D+00
```

### Parameter Definitions (RINEX 3.02 GPS Navigation Message)

**Line 1: Header and Clock Parameters**
| Position | Parameter | Description | Units |
|----------|-----------|-------------|-------|
| Sat ID | `G10` | Satellite identifier (G = GPS, PRN 10) | - |
| Year, Month, Day, Hour, Minute, Second | `2025 12 24 00 00 00` | Epoch of clock parameters (toc) | UTC/GPS |
| Column 4-22 | `af0` = -5.765147507191D-04 | Satellite clock bias at epoch toc | seconds |
| Column 23-41 | `af1` = -3.637978807092D-12 | Satellite clock drift | sec/sec |
| Column 42-60 | `af2` = 0.000000000000D+00 | Satellite clock drift rate | sec/sec² |

**Line 2: Orbit Parameters (1/4)**
| Column | Parameter | Description | Units |
|--------|-----------|-------------|-------|
| 4-22 | `IODE` = 9.0 | Issue of Data, Ephemeris | - |
| 23-41 | `Crs` = -5.968750D+00 | Amplitude of sine harmonic correction term (orbital radius) | meters |
| 42-60 | `Δn` = 3.972665477463D-09 | Mean motion difference from computed value | rad/sec |
| 61-79 | `M0` = -1.234327286869D+00 | Mean anomaly at reference epoch | radians |

**Line 3: Orbit Parameters (2/4)**
| Column | Parameter | Description | Units |
|--------|-----------|-------------|-------|
| 4-22 | `Cuc` = -2.924352884293D-07 | Amplitude of cosine harmonic correction term (argument of latitude) | radians |
| 23-41 | `e` = 1.094881631434D-02 | Eccentricity | - |
| 42-60 | `Cus` = 1.903623342514D-06 | Amplitude of sine harmonic correction term (argument of latitude) | radians |
| 61-79 | `√A` = 5.153646812439D+03 | Square root of semi-major axis | meters^0.5 |

**Line 4: Orbit Parameters (3/4)**
| Column | Parameter | Description | Units |
|--------|-----------|-------------|-------|
| 4-22 | `toe` = 2.592000000000D+05 | Ephemeris reference epoch (time of ephemeris) | seconds of GPS week |
| 23-41 | `Cic` = 2.719461917877D-07 | Amplitude of cosine harmonic correction term (inclination) | radians |
| 42-60 | `Ω0` = -9.103512747561D-01 | Right ascension of ascending node at weekly epoch | radians |
| 61-79 | `Cis` = 1.192092895508D-07 | Amplitude of sine harmonic correction term (inclination) | radians |

**Line 5: Orbit Parameters (4/4)**
| Column | Parameter | Description | Units |
|--------|-----------|-------------|-------|
| 4-22 | `i0` = 9.919594166456D-01 | Inclination angle at reference epoch | radians |
| 23-41 | `Crc` = 3.584687500000D+02 | Amplitude of cosine harmonic correction term (orbital radius) | meters |
| 42-60 | `ω` = -2.277835439618D+00 | Argument of perigee | radians |
| 61-79 | `Ω̇` = -8.024619971918D-09 | Rate of right ascension of ascending node | rad/sec |

**Line 6: Orbit and Week Parameters**
| Column | Parameter | Description | Units |
|--------|-----------|-------------|-------|
| 4-22 | `i̇` = -1.082187934614D-10 | Rate of inclination angle | rad/sec |
| 23-41 | Spare | Reserved for future use | - |
| 42-60 | `GPS Week` = 2.398000000000D+03 | GPS week number | - |
| 61-79 | Spare | Reserved for future use | - |

**Line 7: Signal Health and Time Group Delay**
| Column | Parameter | Description | Units |
|--------|-----------|-------------|-------|
| 4-22 | `URA` = 2.0 | User Range Accuracy index | - |
| 23-41 | `SV Health` = 0.0 | Satellite health status (0 = healthy) | - |
| 42-60 | `TGD` = 2.328306436539D-09 | Group delay differential (L1-L2) | seconds |
| 61-79 | `IODC` = 9.0 | Issue of Data, Clock | - |

**Line 8: Transmission Time**
| Column | Parameter | Description | Units |
|--------|-----------|-------------|-------|
| 4-22 | `Transmission Time` = 2.591700000000D+05 | Message transmission time of week | seconds |
| 23-41 | Spare | Reserved | - |

### Physical Constants for GPS

| Constant | Symbol | Value | Unit |
|----------|--------|-------|------|
| Earth's Gravitational Parameter (WGS84) | μ, GM | 3.986005 × 10¹⁴ | m³/s² |
| Earth's Rotation Rate (WGS84) | Ωₑ | 7.2921151467 × 10⁻⁵ | rad/s |
| Speed of Light | c | 299,792,458 | m/s |
| GPS Week Duration | - | 604,800 | seconds |
| Max time difference for wraparound | - | 302,400 | seconds (±3.5 days) |

### References Documentation

For detailed parameter descriptions and RINEX format specifications, refer to the [Satellite Clock Correction](#satellite-clock-correction) section below.



Satellite clock correction models the bias and drift of the satellite's atomic clock relative to GPS time. This is essential for accurate pseudorange-based positioning.

### Ephemeris Parameters

The broadcast ephemeris includes three clock polynomial coefficients and orbital parameters for relativistic correction:

- **`af0`** - Clock bias at reference epoch [seconds]
- **`af1`** - Clock drift rate [seconds/second]
- **`af2`** - Clock drift rate change [seconds/second²]
- **`toc`** - Clock reference epoch (broadcast time)
- **`e`** - Orbital eccentricity (for relativistic term)
- **`sqrtA`** - Square root of semi-major axis [meters^0.5]

### Clock Correction Formula

The satellite clock correction is computed as:

$$\Delta t_s = a_0 + a_1 \cdot \Delta t + a_2 \cdot (\Delta t)^2 + \Delta t_{rel}$$

where:
- $a_0, a_1, a_2$ are the clock polynomial coefficients
- $\Delta t$ is the time difference from clock reference epoch ($t_{oc}$)
- $\Delta t_{rel}$ is the relativistic clock correction

### Clock Polynomial Term

$$\Delta t_{poly} = a_0 + a_1 \cdot \Delta t + a_2 \cdot (\Delta t)^2$$

This models the satellite's atomic clock behavior, accounting for:
- Initial bias (`af0`)
- Frequency offset/drift (`af1`)
- Frequency drift rate (`af2`, typically very small)

The time difference $\Delta t$ must account for GPS week wraparound (±302400 seconds = ±3.5 days).

### Relativistic Correction Term

The satellite's motion in Earth's gravitational field causes relativistic frequency shift. The relativistic clock correction is:

$$\Delta t_{rel} = \frac{2GM}{c^2} \cdot \frac{e \sqrt{A}}{c^2} \sin E$$

Simplified for GPS:

$$\Delta t_{rel} = 2 F \cdot e \cdot \sqrt{A} \cdot \sin E$$

where:
- $F = -\frac{\sqrt{\mu}}{c^2} \approx -4.4428 \times 10^{-10}$ [sec·m^{-0.5}]
- $\mu = GM = 3.986005 \times 10^{14}$ m³/s² (WGS84 gravitational constant)
- $c = 299792458$ m/s (speed of light)
- $e$ = orbital eccentricity
- $\sqrt{A}$ = square root of semi-major axis [meters^0.5]
- $E$ = eccentric anomaly [radians]

**Physical Interpretation:**
- When satellite is near perigee (E ≈ 0): low velocity, clock runs faster, $\Delta t_{rel} \approx 0$
- When satellite is near apogee (E ≈ π): high velocity, clock runs slower, $\Delta t_{rel}$ is maximum negative
- Magnitude: typically ±38 nanoseconds for GPS (reduces to about ±25 ns after polynomial correction)

### Implementation

```python
# Time difference from clock reference epoch
dt = wrap_time_diff(sow - toc_sow)

# Clock polynomial
dt_poly = af0 + af1 * dt + af2 * dt**2

# Relativistic correction
dt_rel = 2.0 * F_REL * e * sqrtA * sin(E)

# Total clock correction
dt_total = dt_poly + dt_rel
```

### Notes

- The satellite clock correction should **not include TGD (Group Delay Differential)**, as TGD is a code-specific delay correction applied separately during pseudorange processing
- Clock corrections are typically accurate to within 2-5 nanoseconds of the true GPS clock
- For high-precision applications, additional corrections (second-order relativistic effects, gravitational redshift) may be needed

### References

- ICD-GPS-200 (Interface Control Document for GPS), Section 20.3.4.3
- RTKLIB source: `eph2pos()` function
- Montenbruck & Eberhard (2014): "Satellite Orbits: Models, Methods and Applications"

## Satellite Position Calculation

Satellite position is computed from broadcast ephemeris using Kepler's equations of orbital motion. The ephemeris parameters define the satellite's orbit at a specific reference epoch, and orbital equations are propagated to the desired observation time.

### Overview of Position Calculation Steps

1. **Calculate time from ephemeris epoch** ($t_k$)
2. **Compute mean anomaly** ($M$) at observation time
3. **Solve Kepler's equation** to find eccentric anomaly ($E$)
4. **Calculate true anomaly** ($\nu$) from eccentric anomaly
5. **Compute orbital position** in orbital plane
6. **Apply perturbation corrections** (harmonic terms)
7. **Transform to ECEF** coordinates

### Kepler's Equation

Kepler's equation relates mean anomaly ($M$), eccentric anomaly ($E$), and eccentricity ($e$):

$$M = E - e \sin E$$

**Physical interpretation:**
- **Mean Anomaly ($M$)**: Fictitious angle at a constant rate (mean motion) - uniform angular motion
- **Eccentric Anomaly ($E$)**: Intermediate computational variable linking mean motion to true orbit
- **Eccentricity ($e$)**: Orbit shape parameter (0 = circle, 1 = parabola, > 0 = ellipse for satellites)

**The relationship shows:**
- When $E = 0$ (perigee, closest point): $M = 0$
- When $E = \pi$ (apogee, farthest point): $M = \pi$
- Satellite moves faster near perigee (larger $dE$ for same $dM$)

### Kepler Equation Solution Method

Since Kepler's equation is **transcendental**, it must be solved iteratively using Newton-Raphson method:

$$E_{n+1} = E_n - \frac{E_n - e \sin E_n - M}{1 - e \cos E_n}$$

**Convergence:**
- Start with $E_0 = M$
- Iterate until: $|E_{n+1} - E_n| < \epsilon$ (typically $\epsilon = 10^{-12}$ rad)
- Converges in 3-5 iterations for typical GPS eccentricity (0.01-0.02)

**Implementation notes:**
- Use double precision to avoid numerical errors
- Check for iteration count to prevent infinite loops
- For GPS: usually converges in < 2 iterations

### Step-by-Step Calculation with Ephemeris Parameters

#### **Step 1: Time from Ephemeris Epoch**

$$t_k = \text{wrap}(SOW - t_{oe})$$

where:
- `SOW` (Seconds Of Week): Observation time in GPS week seconds
- `toe` (time of ephemeris): Reference epoch = 2.592000000000D+05 sec
- `wrap()`: Account for GPS week wraparound (±302400 sec boundary)

#### **Step 2: Mean Motion and Mean Anomaly**

$$n_0 = \sqrt{\frac{\mu}{A^3}}$$

$$n = n_0 + \Delta n$$

$$M = M_0 + n \cdot t_k$$

**Parameters used from ephemeris:**
- `√A` = 5.153646812439D+03 m^0.5 → Compute $A = (\text{√A})^2$ (semi-major axis)
- `M0` = -1.234327286869D+00 rad (mean anomaly at reference epoch)
- `Δn` = 3.972665477463D-09 rad/sec (mean motion correction)
- `μ` = 3.986005×10¹⁴ m³/s² (WGS84 gravitational parameter - constant)

#### **Step 3: Eccentric Anomaly (Solve Kepler's Equation)**

Iteratively solve: $E - e \sin E = M$

**Parameters used:**
- `e` = 1.094881631434D-02 (eccentricity)
- `M` (from Step 2)

#### **Step 4: True Anomaly**

$$\nu = \arctan2\left(\sqrt{1-e^2} \sin E, \cos E - e\right)$$

#### **Step 5: Orbital Position (Before Perturbations)**

$$\varphi = \nu + \omega$$

$$r_0 = A(1 - e \cos E)$$

$$i_0 = i_0 + \dot{i} \cdot t_k$$

**Parameters used from ephemeris:**
- `ω` = -2.277835439618D+00 rad (argument of perigee)
- `i0` = 9.919594166456D-01 rad (inclination angle at reference)
- `i̇` = -1.082187934614D-10 rad/sec (rate of inclination)

#### **Step 6: Harmonic Perturbation Corrections**

Apply second-order harmonic corrections for small perturbations:

$$\Delta u = C_{us} \sin(2\varphi) + C_{uc} \cos(2\varphi)$$

$$\Delta r = C_{rs} \sin(2\varphi) + C_{rc} \cos(2\varphi)$$

$$\Delta i = C_{is} \sin(2\varphi) + C_{ic} \cos(2\varphi)$$

**Corrected values:**
$$u = \varphi + \Delta u$$
$$r = r_0 + \Delta r$$
$$i = i_0 + \Delta i$$

**Parameters used from ephemeris:**
- `Cus` = 1.903623342514D-06 rad (sine amplitude, argument of latitude)
- `Cuc` = -2.924352884293D-07 rad (cosine amplitude, argument of latitude)
- `Crs` = -5.968750D+00 m (sine amplitude, orbital radius)
- `Crc` = 3.584687500000D+02 m (cosine amplitude, orbital radius)
- `Cis` = 1.192092895508D-07 rad (sine amplitude, inclination)
- `Cic` = 2.719461917877D-07 rad (cosine amplitude, inclination)

#### **Step 7: Orbital Plane to ECEF Transformation**

Position in orbital plane:
$$x' = r \cos u$$
$$y' = r \sin u$$

Right ascension of ascending node (with Earth rotation correction):
$$\Omega = \Omega_0 + (\dot{\Omega} - \Omega_e) t_k - \Omega_e \cdot t_{oe}$$

Transform to ECEF:
$$x = x' \cos\Omega - y' \cos i \sin\Omega$$
$$y = x' \sin\Omega + y' \cos i \cos\Omega$$
$$z = y' \sin i$$

**Parameters used from ephemeris:**
- `Ω0` = -9.103512747561D-01 rad (right ascension of ascending node)
- `Ω̇` = -8.024619971918D-09 rad/sec (rate of Ω)
- `Ωe` = 7.2921151467×10⁻⁵ rad/sec (Earth's rotation rate - constant)
- `toe` (time of ephemeris - from Step 1)
- `i` (inclination - from Step 6)

### Complete Ephemeris Parameter Reference Table

| Parameter | RINEX | Value (Example) | Purpose | Step |
|-----------|-------|-----------------|---------|------|
| Semi-major axis | `√A` | 5.153646812439D+03 m^0.5 | Orbital size | 2,5 |
| Eccentricity | `e` | 1.094881631434D-02 | Orbit shape | 3,4 |
| Inclination | `i0` | 9.919594166456D-01 rad | Orbit orientation | 5,7 |
| RAAN | `Ω0` | -9.103512747561D-01 rad | Ascending node | 7 |
| Argument of perigee | `ω` | -2.277835439618D+00 rad | Perigee location | 5 |
| Mean anomaly | `M0` | -1.234327286869D+00 rad | Initial position | 2 |
| Mean motion correction | `Δn` | 3.972665477463D-09 rad/s | Perturbation | 2 |
| Inclination rate | `i̇` | -1.082187934614D-10 rad/s | Perturbation | 5 |
| RAAN rate | `Ω̇` | -8.024619971918D-09 rad/s | Earth rotation effect | 7 |
| Amplitude corrections | `Cru, Crs, Cic, Cis` | Various | Harmonic corrections | 6 |
| Ephemeris epoch | `toe` | 2.592000000000D+05 s | Reference time | 1,7 |

### Implementation Example (Python)

```python
import numpy as np

def compute_satellite_position(ephemeris, observation_time_sow):
    """
    Compute satellite ECEF position from broadcast ephemeris.

    Args:
        ephemeris: Dict with parameters (√A, e, M0, Δn, i0, ω, Ω0, toe, etc.)
        observation_time_sow: Observation time in seconds of GPS week
    """
    # Constants
    GM = 3.986005e14  # m³/s²
    OMEGA_E = 7.2921151467e-5  # rad/s

    # Step 1: Time from ephemeris epoch
    tk = observation_time_sow - ephemeris['toe']
    if tk > 302400:
        tk -= 604800
    elif tk < -302400:
        tk += 604800

    # Step 2: Mean motion and mean anomaly
    A = ephemeris['sqrtA'] ** 2
    n0 = np.sqrt(GM / (A ** 3))
    n = n0 + ephemeris['delta_n']
    M = ephemeris['M0'] + n * tk

    # Step 3: Solve Kepler's equation (Newton-Raphson)
    E = M
    for _ in range(10):
        f = E - ephemeris['e'] * np.sin(E) - M
        df = 1 - ephemeris['e'] * np.cos(E)
        E_new = E - f / df
        if abs(E_new - E) < 1e-12:
            break
        E = E_new

    # Step 4: True anomaly
    nu = np.arctan2(np.sqrt(1 - ephemeris['e']**2) * np.sin(E),
                    np.cos(E) - ephemeris['e'])

    # Step 5: Orbital position with perturbations
    phi = nu + ephemeris['omega']
    sin2phi = np.sin(2 * phi)
    cos2phi = np.cos(2 * phi)

    u = phi + ephemeris['Cus'] * sin2phi + ephemeris['Cuc'] * cos2phi
    r = A * (1 - ephemeris['e'] * np.cos(E)) + \
        ephemeris['Crs'] * sin2phi + ephemeris['Crc'] * cos2phi
    i = ephemeris['i0'] + ephemeris['idot'] * tk + \
        ephemeris['Cis'] * sin2phi + ephemeris['Cic'] * cos2phi

    # Step 7: Transform to ECEF
    x_prime = r * np.cos(u)
    y_prime = r * np.sin(u)

    Omega = ephemeris['Omega0'] + (ephemeris['Omegadot'] - OMEGA_E) * tk - \
            OMEGA_E * ephemeris['toe']

    cos_i = np.cos(i)
    sin_i = np.sin(i)
    cos_Omega = np.cos(Omega)
    sin_Omega = np.sin(Omega)

    x = x_prime * cos_Omega - y_prime * cos_i * sin_Omega
    y = x_prime * sin_Omega + y_prime * cos_i * cos_Omega
    z = y_prime * sin_i

    return np.array([x, y, z])
```

### Accuracy Notes

- **Position accuracy**: ~2-5 meters (broadcast ephemeris)
- **Best at toe**: Accuracy degrades away from ephemeris reference epoch
- **Age of ephemeris**: Typically valid ±2 hours from toe
- **Higher accuracy**: Use precise/final ephemeris from IGS for mm-level accuracy
