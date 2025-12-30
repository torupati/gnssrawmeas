"""GNSS physical constants and derived wavelengths.

Keep computation separate from plotting, so other modules can import
these values without circular dependencies.
"""

CLIGHT: float = 299_792_458.0

# L-band carrier frequencies (Hz)
L1_FREQ: float = 1.57542e9
L2_FREQ: float = 1.22760e9
L5_FREQ: float = 1.17645e9

# Wavelengths (m)
wlen_L1: float = CLIGHT / L1_FREQ
wlen_L2: float = CLIGHT / L2_FREQ
wlen_L5: float = CLIGHT / L5_FREQ

# Wide- and Narrow-lane effective wavelengths (m)
wl_wlen: float = CLIGHT / (L1_FREQ - L2_FREQ)
nl_wlen: float = CLIGHT / (L1_FREQ + L2_FREQ)

# Iono-free combined effective wavelength (m)
iono_wlen: float = (L1_FREQ**2) / (L1_FREQ**2 - L2_FREQ**2) * wlen_L1 + (
    (L2_FREQ**2) / (L1_FREQ**2 - L2_FREQ**2)
) * wlen_L2
