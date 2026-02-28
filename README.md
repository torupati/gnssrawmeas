# GNSS Remote Sensing Project

This is my personal project of GNSS remote sensing.
GNSS RINEX observation plotting and raw measurement analysis.

This project uses **uv** for dependency and environment management.

## RINEX Format Specifications

- [RINEX 3.04](https://files.igs.org/pub/data/format/rinex304.pdf) - Widely used version
- [RINEX 3.05](https://files.igs.org/pub/data/format/rinex305.pdf) - Latest version

## Reference Textbook

- [ESA GNSS Book, Volume I (TM-23)](https://gssc.esa.int/navipedia/GNSS_Book/ESA_GNSS-Book_TM-23_Vol_I.pdf) - Comprehensive GNSS fundamentals and measurement theory.

## Documentation

### GNSS Fundamentals
- [GNSS Frequencies](doc/gnss_frequencies.md) - GNSS signal frequency specifications and wavelengths
- [Ranging Signals](doc/ranging_sianals.md) - Overview of ranging signal codes and characteristics
- [Computation Reference](doc/computation_reference.md) - Mathematical references and computation formulas

### Signal Processing
- [Carrier-Code Smoothing](doc/code_carrier_smoothing.md) - Carrier phase smoothing techniques for pseudorange
- [Widelane Combination](doc/widelane_combination.md) - Widelane and ionosphere-free signal combinations
- [RTCM3 Format](doc/rtcm3.md) - RTCM3 message format and implementation
