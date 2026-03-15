#!/usr/bin/env python3
"""Example script demonstrating GNSS database usage.

This script shows how to:
1. Parse RINEX observation files
2. Save observations to SQLite database
3. Load observations from database
4. Compute and save SPP solutions
5. Query database statistics

Usage:
    python examples/database_example.py <rinex_obs> <rinex_nav> [--db <database_path>]
"""

import argparse
import json
from logging import getLogger, basicConfig, INFO
from pathlib import Path

from app.gnss.database import GnssDatabase
from app.gnss.satellite_signals import parse_rinex_observation_file

# Import SPP functionality if available
try:
    from app.spp import parse_rinex_navigation_file, single_point_positioning

    SPP_AVAILABLE = True
except ImportError:
    SPP_AVAILABLE = False

logger = getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="GNSS Database Example - Parse RINEX and store in SQLite"
    )
    parser.add_argument("rinex_obs", type=str, help="RINEX observation file")
    parser.add_argument(
        "rinex_nav", type=str, nargs="?", help="RINEX navigation file (optional)"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="gnss_data.db",
        help="SQLite database file path (default: gnss_data.db)",
    )
    parser.add_argument(
        "--signal-code-map",
        type=str,
        default=str(Path(__file__).parent.parent / "app" / ".signal_code_map.json"),
        help="Path to signal code map JSON",
    )
    parser.add_argument(
        "--max-epochs",
        type=int,
        default=0,
        help="Limit number of epochs to process (0 = all)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing database before saving",
    )

    args = parser.parse_args()
    basicConfig(level=INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # Validate input files
    obs_path = Path(args.rinex_obs)
    if not obs_path.exists():
        logger.error("RINEX observation file not found: %s", obs_path)
        return 1

    nav_path = None
    if args.rinex_nav:
        nav_path = Path(args.rinex_nav)
        if not nav_path.exists():
            logger.error("RINEX navigation file not found: %s", nav_path)
            return 1

    signal_code_map_path = Path(args.signal_code_map)
    if not signal_code_map_path.exists():
        logger.error("Signal code map not found: %s", signal_code_map_path)
        return 1

    # Load signal code map
    with signal_code_map_path.open("r", encoding="utf-8") as f:
        signal_code_map = json.load(f)

    # Initialize database
    db_path = Path(args.db)
    logger.info("Database: %s", db_path.absolute())
    db = GnssDatabase(db_path)

    # Clear database if requested
    if args.clear:
        logger.info("Clearing existing database...")
        db.clear_database()

    # Show initial statistics
    logger.info("Initial database statistics:")
    stats = db.get_statistics()
    for key, value in stats.items():
        logger.info("  %s: %s", key, value)

    # Parse RINEX observation file
    logger.info("Parsing RINEX observation file: %s", obs_path)
    epochs = parse_rinex_observation_file(str(obs_path), signal_code_map)

    if args.max_epochs > 0:
        epochs = epochs[: args.max_epochs]

    logger.info("Parsed %d epochs", len(epochs))

    if not epochs:
        logger.warning("No epochs parsed from RINEX file")
        return 0

    # Show time range
    first_dt = epochs[0].datetime
    last_dt = epochs[-1].datetime
    logger.info("Time range: %s to %s", first_dt, last_dt)
    logger.info("Duration: %.1f seconds", (last_dt - first_dt).total_seconds())

    # Save observations to database
    logger.info("Saving observations to database...")
    db.save_epoch_observations(epochs)
    logger.info("Successfully saved %d epochs", len(epochs))

    # Compute and save SPP solutions if navigation file is provided
    if nav_path and SPP_AVAILABLE:
        logger.info("Computing SPP solutions...")
        nav_data = parse_rinex_navigation_file(str(nav_path))
        solutions = single_point_positioning(epochs, nav_data)

        logger.info("Saving SPP solutions to database...")
        for sol in solutions:
            solution_data = {
                "position_ecef": sol.position_ecef,
                "position_llh": sol.position_llh,
                "clock_bias_m": sol.clock_bias_m,
                "num_satellites": sol.num_sats,
                "residuals": sol.residuals,
            }
            db.save_spp_solution(solution_data, sol.datetime)

        logger.info("Successfully saved %d SPP solutions", len(solutions))

        # Print some solution statistics
        if solutions:
            valid_sols = [s for s in solutions if s.num_sats >= 4]
            if valid_sols:
                lat_vals = [s.position_llh[0] for s in valid_sols]
                lon_vals = [s.position_llh[1] for s in valid_sols]
                h_vals = [s.position_llh[2] for s in valid_sols]

                logger.info("SPP Solution Statistics:")
                logger.info(
                    "  Valid solutions: %d / %d", len(valid_sols), len(solutions)
                )
                logger.info(
                    "  Latitude:  mean=%.7f°, std=%.7f°",
                    sum(lat_vals) / len(lat_vals),
                    (
                        sum((x - sum(lat_vals) / len(lat_vals)) ** 2 for x in lat_vals)
                        / len(lat_vals)
                    )
                    ** 0.5,
                )
                logger.info(
                    "  Longitude: mean=%.7f°, std=%.7f°",
                    sum(lon_vals) / len(lon_vals),
                    (
                        sum((x - sum(lon_vals) / len(lon_vals)) ** 2 for x in lon_vals)
                        / len(lon_vals)
                    )
                    ** 0.5,
                )
                logger.info(
                    "  Height:    mean=%.3f m, std=%.3f m",
                    sum(h_vals) / len(h_vals),
                    (
                        sum((x - sum(h_vals) / len(h_vals)) ** 2 for x in h_vals)
                        / len(h_vals)
                    )
                    ** 0.5,
                )

    # Show final statistics
    logger.info("Final database statistics:")
    stats = db.get_statistics()
    for key, value in stats.items():
        logger.info("  %s: %s", key, value)

    # Demonstrate loading data back
    logger.info("Demonstrating data retrieval...")
    loaded_epochs = db.load_epoch_observations(
        start_datetime=first_dt,
        end_datetime=first_dt,
    )
    if loaded_epochs:
        logger.info("Successfully loaded first epoch: %s", loaded_epochs[0].datetime)
        logger.info("  GPS satellites: %d", len(loaded_epochs[0].satellites_gps))
        logger.info(
            "  Galileo satellites: %d", len(loaded_epochs[0].satellites_galileo)
        )
        logger.info(
            "  GLONASS satellites: %d", len(loaded_epochs[0].satellites_glonass)
        )
        logger.info("  QZSS satellites: %d", len(loaded_epochs[0].satellites_qzss))

        # Show details of first satellite
        for sat_id, sat_obs in loaded_epochs[0].iter_satellites():
            logger.info("  Satellite %s:", sat_id)
            logger.info("    Signals: %s", list(sat_obs.signals.keys()))
            logger.info("    Ambiguities: %s", list(sat_obs.ambiguities.keys()))
            break  # Only show first satellite

    logger.info("Database example completed successfully!")
    logger.info("Database saved at: %s", db_path.absolute())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
