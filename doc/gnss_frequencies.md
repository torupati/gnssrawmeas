# GNSS Frequency Reference

This table summarizes commonly used GNSS carrier frequencies and their nominal center frequencies.

| GNSS System | Signal Band | Signal Name(s) | Center Frequency (MHz) | Lower Frequency (MHz) | Upper Frequency (MHz) | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| GPS | L1 | L1 C/A, L1 P(Y), L1C | 1575.42 | 1574.397 | 1576.443 | Legacy civil and military signals |
| GPS | L2 | L2 P(Y), L2C | 1227.60 | 1226.577 | 1228.623 | Range shown for L2C (civil) |
| GPS | L5 | L5 | 1176.45 | 1166.220 | 1186.680 | Safety-of-life signal |
| GLONASS | G1 (L1) | L1 C/A, L1 P | 1602.00 + k×0.5625 | 1598.0625 | 1605.3750 | FDMA; k = -7..+6 |
| GLONASS | G2 (L2) | L2 C/A, L2 P | 1246.00 + k×0.4375 | 1242.9375 | 1248.6250 | FDMA; k = -7..+6 |
| GLONASS | G3 (L3) | L3 | 1202.025 | 1201.002 | 1203.048 | CDMA signal |
| Galileo | E1 | E1-B, E1-C | 1575.42 | 1574.397 | 1576.443 | Overlaps GPS L1 |
| Galileo | E5a | E5a | 1176.45 | 1166.220 | 1186.680 | Overlaps GPS L5 |
| Galileo | E5b | E5b | 1207.14 | 1196.910 | 1217.370 | Galileo E5b center frequency |
| Galileo | E5 (AltBOC) | E5a+E5b | 1191.795 | 1164.000 | 1215.000 | Wideband AltBOC |
| Galileo | E6 | E6-B, E6-C | 1278.75 | 1268.520 | 1288.980 | Commercial service |
| BeiDou (BDS) | B1I | B1I | 1561.098 | 1559.052 | 1563.144 | Legacy BDS signal |
| BeiDou (BDS) | B1C | B1C | 1575.42 | 1574.397 | 1576.443 | Interoperable with GPS L1/Galileo E1 |
| BeiDou (BDS) | B2I | B2I | 1207.14 | 1205.094 | 1209.186 | Legacy BDS signal |
| BeiDou (BDS) | B2a | B2a | 1176.45 | 1166.220 | 1186.680 | Interoperable with GPS L5/Galileo E5a |
| BeiDou (BDS) | B2b | B2b | 1207.14 | 1196.910 | 1217.370 | Interoperable with Galileo E5b |
| BeiDou (BDS) | B3I | B3I | 1268.52 | 1258.290 | 1278.750 | Regional/open services |
| QZSS | L1 | L1C/A, L1C | 1575.42 | 1574.397 | 1576.443 | Interoperable with GPS L1 |
| QZSS | L2 | L2C | 1227.60 | 1226.577 | 1228.623 | Interoperable with GPS L2C |
| QZSS | L5 | L5 | 1176.45 | 1166.220 | 1186.680 | Interoperable with GPS L5 |
| QZSS | L6 | L6 (LEX) | 1278.75 | 1268.520 | 1288.980 | High-precision service |
| NavIC (IRNSS) | L5 | L5 | 1176.45 | 1166.220 | 1186.680 | Regional system |
| NavIC (IRNSS) | S | S | 2492.028 | 2483.500 | 2500.000 | Regional system (S-band allocation) |
| SBAS | L1 | L1 | 1575.42 | 1574.397 | 1576.443 | Augmentation on L1 |
| SBAS | L5 | L5 | 1176.45 | 1166.220 | 1186.680 | Augmentation on L5 |

Ranges are approximate occupied bandwidths for the primary civil signal in each band unless noted; GLONASS ranges are min/max across FDMA channels.

## L7 and L8 Frequency Bands

While GPS traditionally uses L1, L2, and L5, the broader GNSS community has adopted additional frequency bands:

### L7 Band (~1207.14 MHz)
The L7 designation refers to frequencies in the 1207.14 MHz band:
- **Galileo E5b**: 1207.14 MHz (European system)
- **BeiDou B2b**: 1207.14 MHz (Chinese system)
- **GLONASS G3**: 1202.025 MHz (Russian system - adjacent band)

This band is used for high-accuracy and open-service positioning signals.

### L8 Band (~1278.75 MHz)
The L8 designation refers to frequencies in the 1278.75 MHz band:
- **QZSS L6**: 1278.75 MHz (Japanese system - high-precision LEX service)
- **Galileo E6**: 1278.75 MHz (European system - commercial/safety-critical signals)
- **BeiDou B3I**: 1268.52 MHz (Chinese system - regional/open services, adjacent band)

This band is typically reserved for authenticated, high-precision, or safety-critical applications.

### Wavelength Reference
For signal processing, the wavelengths corresponding to these bands are:
- **L7 (1207.14 MHz)**: λ = 0.260476 m (Galileo E5b, also called L7)
- **L8 (1278.75 MHz)**: λ = 0.209375 m (QZSS L6, Galileo E6, also called L8)
