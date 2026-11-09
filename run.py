"""Main entry point for LG Smart Cottage PV/ESS/AWHP ROI Calculation.

Usage:
    python run.py --country korea
"""

import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd

from engine.schema import load_country_config
from engine.weather import load_weather_data
from engine.scenarios import run_all_scenarios
from engine.report import generate_outputs


def main():
    parser = argparse.ArgumentParser(description="Run Smart Cottage PV/ESS/AWHP ROI Calculation")
    parser.add_argument(
        "--country",
        type=str,
        default="korea",
        help="Country directory name to run (default: korea)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    country_dir = project_root / args.country

    if not country_dir.exists():
        print(f"Error: Country directory '{args.country}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading configuration for country: {args.country}...")
    country_config = load_country_config(country_dir)

    print(f"Configuration loaded: {len(country_config.values)} categories.")
    print(f"PLACEHOLDER status: {country_config.placeholder_count} items.")
    print(f"UNVERIFIED status: {country_config.unverified_count} items.")

    weather_file_rel = country_config.values["country"]["weather_file"]
    weather_path = project_root / weather_file_rel
    print(f"Loading weather dataset: {weather_path}...")
    weather_df = load_weather_data(weather_path)
    annual_ghi = float(weather_df["ghi"].sum() * 0.25 / 1000.0)

    print("Running full scenario simulations (432 scenarios + DUO Max incremental)...")
    df_results, df_duo_inc, saved_profiles, verification_data = run_all_scenarios(
        config_values=country_config.values,
        weather_df=weather_df,
        placeholders_list=country_config.placeholders,
        unverifieds_list=country_config.unverifieds,
    )

    output_dir = country_dir / "output"
    print(f"Generating output files and charts in: {output_dir}...")
    generate_outputs(
        df_results=df_results,
        df_duo_inc=df_duo_inc,
        saved_profiles=saved_profiles,
        verification_data=verification_data,
        output_dir=output_dir,
        config_placeholders=country_config.placeholders,
        config_unverifieds=country_config.unverifieds,
        weather_file_path=str(weather_path),
        annual_ghi=annual_ghi,
    )

    print("\n[SUCCESS] Completed scenario ROI computations.")
    print(f"- Output Full CSV: {output_dir / 'results_all.csv'} (Rows: {len(df_results)})")
    print(f"- DUO Max Incremental CSV: {output_dir / 'results_duomax_incremental.csv'} (Rows: {len(df_duo_inc)})")
    print(f"- Summary: {output_dir / 'results_summary.md'}")
    print(f"- Validation: {output_dir / 'validation.md'}")
    print(f"- Profiles: {output_dir / 'profiles'}")
    print(f"- Charts: {output_dir / 'charts'}")


if __name__ == "__main__":
    main()
