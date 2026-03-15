# GNSS Database Examples

This directory contains example scripts demonstrating how to use the GNSS database module.

## database_example.py

Example script showing how to:
- Parse RINEX observation files
- Save observations to SQLite database
- Load observations from database
- Compute and save SPP (Single Point Positioning) solutions
- Query database statistics

### Usage

```bash
# Basic usage - save RINEX observations to database
python examples/database_example.py data/observation.rnx --db output/gnss_data.db

# With navigation file for SPP computation
python examples/database_example.py data/observation.rnx data/navigation.rnx --db output/gnss_data.db

# Clear existing database before saving
python examples/database_example.py data/observation.rnx --db output/gnss_data.db --clear

# Limit number of epochs processed
python examples/database_example.py data/observation.rnx --db output/gnss_data.db --max-epochs 100
```

### Requirements

- RINEX observation file (version 3.x)
- Optional: RINEX navigation file for SPP computation
- Signal code map JSON file (default: `app/.signal_code_map.json`)

### Output

The script will:
1. Parse the RINEX file and display time range and number of epochs
2. Save all observations to the SQLite database
3. Optionally compute and save SPP solutions if navigation file is provided
4. Display database statistics (number of epochs, satellites, signals, etc.)
5. Demonstrate loading data back from the database

### Example Output

```
2024-03-15 12:00:00 - INFO - Database: /path/to/gnss_data.db
2024-03-15 12:00:00 - INFO - Parsing RINEX observation file: data/observation.rnx
2024-03-15 12:00:01 - INFO - Parsed 1800 epochs
2024-03-15 12:00:01 - INFO - Time range: 2024-01-15 00:00:00+00:00 to 2024-01-15 00:29:59+00:00
2024-03-15 12:00:01 - INFO - Duration: 1799.0 seconds
2024-03-15 12:00:01 - INFO - Saving observations to database...
2024-03-15 12:00:05 - INFO - Successfully saved 1800 epochs
2024-03-15 12:00:05 - INFO - Final database statistics:
2024-03-15 12:00:05 - INFO -   num_epochs: 1800
2024-03-15 12:00:05 - INFO -   num_satellites: 14400
2024-03-15 12:00:05 - INFO -   num_signals: 28800
2024-03-15 12:00:05 - INFO -   num_ambiguities: 14400
```

## Database Structure

The database uses a normalized schema with the following tables:

- `epochs` - Observation epochs (timestamps)
- `satellites` - Satellite observations for each epoch
- `signals` - Signal measurements (pseudorange, carrier phase, doppler, SNR)
- `ambiguities` - Dual-frequency ambiguity observations
- `satellite_positions` - Computed satellite positions (optional)
- `spp_solutions` - Single point positioning results (optional)

For detailed documentation, see [doc/database.md](../doc/database.md).
