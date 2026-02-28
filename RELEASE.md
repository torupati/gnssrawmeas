# Release v0.1.0

**Release Date**: February 28, 2026

## Overview

Initial release of `gnssraw` - A Python library for GNSS RINEX observation plotting and raw measurement analysis.

This version provides foundational capabilities for processing and analyzing Global Navigation Satellite System (GNSS) measurements from RINEX format files.

## Key Features

### Core Functionality
- **RINEX Observation Processing**: Parse and process GNSS RINEX 3.04/3.05 format files
- **Raw Measurement Analysis**: Analyze satellite signals and observables
- **Data Visualization**: Plot GNSS observations with matplotlib integration
- **Signal Processing**: Support for GPS, GLONASS, Galileo, and BeiDou signals
- **Ambiguity Resolution**: Lambda method implementation for integer ambiguity fixing

### Signal Processing
- Carrier-code smoothing techniques
- Widelane and ionosphere-free signal combinations
- Doppler and pseudorange measurements
- Code and carrier phase observations

### Command-Line Interface
- `rnxproc`: Processing script for RINEX files
- `spp`: Single point positioning calculations
- `--plot-goodstyle`: Light and minimal visualization option

## Dependencies

- Python >= 3.10
- georinex >= 1.16.1
- matplotlib >= 3.7.1
- pyrtcm >= 1.1.10

## Development Dependencies

- pre-commit >= 3.5.0
- ruff >= 0.14.10
- pytest >= 7.0.0
- pytest-cov >= 4.0.0
- mypy >= 1.14.1

## Testing

Comprehensive test suite included with pytest coverage. Tests can be validated by running the CI pipeline or via `make test-cov` locally.

## Documentation

See [doc/](doc/) directory for detailed technical documentation:
- [GNSS Frequencies](doc/gnss_frequencies.md)
- [Ranging Signals](doc/ranging_sianals.md)
- [Carrier-Code Smoothing](doc/code_carrier_smoothing.md)
- [Ionosphere-Free Combinations](doc/ionospherefree_combination.md)
- [Widelane Combinations](doc/widelane_combination.md)
- [RTCM3 Format](doc/rtcm3.md)

## Known Limitations

- First stable release may have edge cases in handling diverse RINEX formats
- Performance optimization ongoing for large observation datasets
- RTCM3 message support is experimental

## Getting Started

1. Visit [README.md](README.md) for installation and usage instructions
2. Check [Documentation](#documentation) for technical details
3. Review [CHANGELOG.md](CHANGELOG.md) for initial feature set

## Future Roadmap

- Enhanced multi-constellation support
- Real-time positioning engine
- Atmospheric modeling and correction
- Network FIX and satellite orbit integration
- PyPI package distribution

## Contributors

- torupa (xpt77@outlook.com)

## License

See [LICENSE](LICENSE) file for details.
