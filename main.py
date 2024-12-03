import argparse
from datetime import datetime
from scanner import BitDevsRadar
from views import (
    generate_category_view,
    generate_domain_view,
    generate_date_view,
    save_detailed_view,
)
from loguru import logger
import sys
import json


def setup_logging(debug_mode: bool = False):
    """Configure logging settings based on debug mode."""
    # Remove default handler
    logger.remove()

    # Set default level to INFO unless debug mode is enabled
    log_level = "DEBUG" if debug_mode else "INFO"

    # Add stderr handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
    )

    # Add file handler
    logger.add(
        "bitdevs_radar.log",
        rotation="1 day",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level,
    )


def load_json_data(json_path: str) -> dict:
    """Load data from a JSON file."""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON file: {e}")
        raise


def generate_views(data: dict, args: argparse.Namespace) -> None:
    """Generate all views from the provided data."""
    logger.info("Generating views")

    # Save detailed view if needed
    if not args.detailed_input or args.detailed_output != args.detailed_input:
        save_detailed_view(data, args.detailed_output)

    # Generate all markdown views
    generate_category_view(data, args.category_output)
    generate_domain_view(data, args.domain_output)
    generate_date_view(data, args.date_output)


def scan_repositories(args: argparse.Namespace, start_date: datetime) -> dict:
    """Scan repositories and return the collected data."""
    logger.debug(f"Configuration file: {args.config}")
    logger.debug(f"Exclusion file: {args.exclude}")

    with BitDevsRadar(
        config_path=args.config,
        exclude_domains_path=args.exclude,
        start_date=start_date,
    ) as radar:
        radar.scan_all_repos()
        return radar.scanned_resources


def main():
    parser = argparse.ArgumentParser(description="Generate BitDevs resource views")
    parser.add_argument(
        "--config",
        default="bitdevs.yaml",
        help="Path to bitdevs.yaml config file",
    )
    parser.add_argument(
        "--exclude",
        default="exclude_domains.yaml",
        help="Path to exclude_domains.yaml file",
    )
    parser.add_argument(
        "--detailed-output",
        default="bitdevs_resources.json",
        help="Output path for detailed JSON view",
    )
    parser.add_argument(
        "--detailed-input",
        help="Input path for pre-existing JSON data. If provided, skips scanning.",
    )
    parser.add_argument(
        "--category-output",
        default="bitdevs_resources.md",
        help="Output path for categorized markdown view",
    )
    parser.add_argument(
        "--domain-output",
        default="bitdevs_domains.md",
        help="Output path for domain-focused markdown view",
    )
    parser.add_argument(
        "--date-output",
        default="bitdevs_dates.md",
        help="Output path for date-focused markdown view",
    )
    parser.add_argument("--start-date", help="Start date in YYYY-MM-DD format")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Setup logging based on debug flag
    setup_logging(args.debug)

    logger.info("Starting BitDevs Resource Radar")

    try:
        # Parse start date if provided
        start_date = None
        if args.start_date:
            try:
                start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
                logger.info(f"Filtering resources from {start_date}")
            except ValueError as e:
                logger.error(f"Invalid date format: {e}")
                return

        # Get data either from input file or by scanning
        if args.detailed_input:
            logger.info(f"Loading pre-existing data from {args.detailed_input}")
            data = load_json_data(args.detailed_input)
        else:
            data = scan_repositories(args, start_date)

        # Generate all views
        generate_views(data, args)

    except Exception as e:
        logger.exception(f"An error occurred during execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
