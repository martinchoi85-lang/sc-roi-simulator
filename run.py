"""Main entry point for LG Smart Cottage PV/ESS/AWHP ROI Calculation (v9).

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
from engine.report import generate_v9_outputs
from engine.run_id import compute_run_id


def main():
    parser = argparse.ArgumentParser(description="Run Smart Cottage PV/ESS/AWHP ROI Calculation v9")
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

    # Compute run_id at the very start to guarantee clean working tree
    run_id = compute_run_id(country_dir)
    print(f"Locked run_id: {run_id}")

    print(f"Loading configuration for country: {args.country}...")
    country_config = load_country_config(country_dir)

    print(f"Configuration loaded: {len(country_config.values)} categories.")
    print(f"PLACEHOLDER status: {country_config.placeholder_count} items.")
    print(f"UNVERIFIED status: {country_config.unverified_count} items.")
    print(f"ASSUMPTION status: {country_config.assumption_count} items.")

    weather_file_rel = country_config.values["country"]["weather_file"]
    weather_path = project_root / weather_file_rel
    print(f"Loading weather dataset: {weather_path}...")
    weather_df = load_weather_data(weather_path)
    annual_ghi = float(weather_df["ghi"].sum() * 0.25 / 1000.0)

    print("Running full scenario simulations (420 scenarios across 7 pairs x 2 heating x 5 occupancies x 3 targets x 2 subsidies)...")
    kosis_dir = country_dir / "source" / "kosis"
    df_results, df_energy_comp, df_ze_sizing, metadata = run_all_scenarios(
        config_values=country_config.values,
        weather_df=weather_df,
        placeholders_list=country_config.placeholders,
        unverifieds_list=country_config.unverifieds,
        assumptions_list=country_config.assumptions,
        kosis_dir=kosis_dir,
    )

    output_dir = country_dir / "output"
    report_dir = country_dir / "report"
    print(f"Generating output files and charts in: {output_dir}...")
    generate_v9_outputs(
        df_results=df_results,
        df_energy_comp=df_energy_comp,
        df_ze_sizing=df_ze_sizing,
        metadata=metadata,
        output_dir=output_dir,
        report_dir=report_dir,
        config_values=country_config.values,
        config_placeholders=country_config.placeholders,
        config_unverifieds=country_config.unverifieds,
        config_assumptions=country_config.assumptions,
        weather_df=weather_df,
        annual_ghi=annual_ghi,
        run_id=run_id,
    )

    print("\n[SUCCESS] Completed v9 scenario ROI computations and reports.")
    print(f"- Output Full CSV: {output_dir / 'results_all.csv'} (Rows: {len(df_results)})")
    print(f"- Energy Comparison CSV: {output_dir / 'energy_comparison.csv'} (Rows: {len(df_energy_comp)})")
    print(f"- Zero Energy Sizing CSV: {output_dir / 'ze_sizing.csv'} (Rows: {len(df_ze_sizing)})")
    print(f"- Summary: {output_dir / 'results_summary.md'}")
    print(f"- Validation: {output_dir / 'validation.md'}")
    print(f"- Report Data: {report_dir / 'report_data.json'}")
    print(f"- HTML Report: {report_dir / 'LG_SC_Korea_ROI_Report.html'}")


if __name__ == "__main__":
    main()
