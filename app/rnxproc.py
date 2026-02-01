import argparse
import json
from pathlib import Path
from logging import getLogger, basicConfig, INFO


from app.gnss.satellite_signals import (
    EpochObservations,
    parse_rinex_observation_file,
    save_gnss_observations_to_json,
)
from app.gnss.plot.observables import plot_satellite_observations

logger = getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Process RINEX observation files and generate plots"
    )
    parser.add_argument("rinex_obs", type=str, help="Path to RINEX observation file")
    parser.add_argument(
        "--outdir",
        type=str,
        default="./out/",
        help="Output directory for plots (default: ./out/)",
    )
    parser.add_argument(
        "--json",
        type=str,
        help="Save parsed data to JSON file (specify output file path)",
    )
    parser.add_argument(
        "--plot-mode",
        type=int,
        choices=[1, 2, 3, 4],
        default=1,
        help=(
            "Plot data selection: 1=all, 2=SNR+widelane only, "
            "3=SNR+widelane+ionofree only, 4=PR+CP+Doppler+SNR only"
        ),
    )
    parser.add_argument(
        "--skip-plot",
        action="store_true",
        help="Skip generating plots",
    )
    parser.add_argument(
        "--signal-code-map",
        type=str,
        default=str(Path(__file__).parent / ".signal_code_map.json"),
        help=(
            "Path to JSON file that defines signal_code_map "
            "(default: .signal_code_map.json)"
        ),
    )

    args = parser.parse_args()

    # Setup logging
    basicConfig(level=INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # Check if input file exists
    rinex_path = Path(args.rinex_obs)
    if not rinex_path.exists():
        logger.error(f"RINEX file not found: {rinex_path}")
        return 1

    # Create output directory if it doesn't exist
    output_dir = Path(args.outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Load signal code map
    signal_code_map_path = Path(args.signal_code_map)
    if not signal_code_map_path.exists():
        logger.error(f"Signal code map file not found: {signal_code_map_path}")
        return 1
    try:
        with signal_code_map_path.open("r", encoding="utf-8") as f:
            signal_code_map = json.load(f)
    except json.JSONDecodeError as exc:
        logger.error(
            f"Invalid JSON in signal code map file: {signal_code_map_path} ({exc})"
        )
        return 1

    # Parse RINEX file
    logger.info(f"Parsing RINEX file: {rinex_path}")
    epochs: list[EpochObservations] = parse_rinex_observation_file(
        str(rinex_path), signal_code_map
    )
    logger.info(
        f"... parsed {len(epochs)} epochs. {epochs[0].datetime if epochs else 'N/A'} to {epochs[-1].datetime if epochs else 'N/A'}"
    )

    # Save to JSON if requested
    if args.json:
        json_output_path = Path(args.json)
        save_gnss_observations_to_json(epochs, json_output_path)
        logger.info(f"Saved parsed data to JSON: {json_output_path}")

    # Generate plots
    if args.skip_plot:
        logger.info("Skipping plot generation (--skip-plot)")
    else:
        logger.info("Generating plots...")
        plot_satellite_observations(epochs, output_dir, plot_mode=args.plot_mode)

    logger.info("Done!")
    return 0


if __name__ == "__main__":
    exit(main())
