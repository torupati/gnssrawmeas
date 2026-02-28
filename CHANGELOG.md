# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-28

### Added

#### Core Features
- Initial release of gnss-remote-sensing library
- RINEX 3.04/3.05 observation file parsing and processing
- Core GNSS measurement analysis capabilities
- Signal combination support (widelane, ionosphere-free)
- Carrier-code smoothing techniques
- Lambda method for integer ambiguity resolution
- Matplotlib-based GNSS observation visualization
- RTCM3 message format support (experimental)

#### Command-Line Tools
- `rnxproc`: RINEX processing engine with flexible output options
- `spp`: Single point positioning calculations
- `--plot-goodstyle`: Minimal plot styling option for cleaner visualizations

#### Module Structure
- `app.rnxproc`: RINEX processing module
- `app.spp`: Single point positioning module
- `app.gnss`: Core GNSS algorithms package
  - `ambiguity.py`: Integer ambiguity resolution (Lambda method)
  - `coordinates.py`: Coordinate system transformations
  - `ephemeris.py`: Ephemeris calculations and orbit models
  - `epoch_series.py`: Time series operations on GNSS observations
  - `rtcm3.py`: RTCM3 message handling and decoding
  - `satellite_signals.py`: GNSS signal definitions and properties
  - `signal_combination.py`: Signal combination algorithms
  - `constants.py`: Physical constants and GNSS parameters

#### Testing & Quality
- Comprehensive test suite with pytest
- Type checking with mypy
- Code linting with ruff
- Pre-commit hooks for code quality
- CI/CD pipeline support (Makefile targets)

#### Documentation
- Project README with feature overview
- Technical documentation:
  - GNSS Frequencies reference
  - Ranging Signals overview
  - Carrier-Code Smoothing guide
  - Ionosphere-Free Combinations
  - Widelane Combinations
  - RTCM3 Format specification
  - Computation reference
  - Developer guide
- Sample data and test datasets
- Release notes and changelog

#### Project Infrastructure
- `pyproject.toml`: Modern Python packaging configuration
- `.gitignore`: Comprehensive ignore rules
- `pytest.ini`: Test configuration
- `Makefile`: Development and CI automation targets
- Pre-commit configuration for automatic checks

### Known Limitations

- RTCM3 support is experimental and may have edge cases
- Some RINEX format variants may require additional testing
- Large observation datasets may benefit from performance optimization

### Notes for Users

This is the first stable release of gnss-remote-sensing. The API is considered stable, but
users should report any unexpected behavior or edge cases encountered.

Sample data is included in `sample_data/` for testing and learning purposes.

---

## Version History

- **0.1.0**: Initial stable release (2026-02-28)
  - Foundation for GNSS observation processing and analysis
