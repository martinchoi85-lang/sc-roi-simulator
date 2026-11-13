"""Main entry point for LG Smart Cottage PV/ESS/AWHP ROI Calculation (v9).

Usage:
    python run.py --country korea
    python run.py --country korea --from 4
"""

import argparse
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd

from engine.schema import load_country_config
from engine.weather import load_weather_data
from engine.run_id import compute_run_id
from engine.pipeline import (
    run_step1_load,
    run_step2_thermal,
    run_step3_sizing,
    run_step3b_dispatch,
    run_step4_cashflow,
    run_step5_report,
)


def main():
    parser = argparse.ArgumentParser(description="Run Smart Cottage PV/ESS/AWHP ROI Calculation v9")
    parser.add_argument(
        "--country",
        type=str,
        default="korea",
        help="Country directory name to run (default: korea)",
    )
    parser.add_argument(
        "--from-step", "--from",
        dest="from_step",
        type=int,
        default=1,
        choices=[1, 2, 3, 4, 5],
        help="Run pipeline starting from specified step (1..5, default: 1)",
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

    kosis_dir = country_dir / "source" / "kosis"
    cache_dir = country_dir / "cache"
    out_dir = country_dir / "output"
    report_dir = country_dir / "report"

    print(f"\n=======================================================")
    print(f"Starting 5-Step ROI Pipeline (Running from Step {args.from_step})")
    print(f"=======================================================")

    step_timings = {}
    pipe_t0 = time.perf_counter()

    # Step 1: 부하·재실
    step1_data, t1, s1 = run_step1_load(
        config_values=country_config.values,
        weather_df=weather_df,
        kosis_dir=kosis_dir,
        cache_dir=cache_dir,
        from_step=args.from_step,
    )
    step_timings["step1"] = (t1, s1)

    # Step 2: 열 계산
    step2_data, t2, s2 = run_step2_thermal(
        config_values=country_config.values,
        weather_df=weather_df,
        step1_data=step1_data,
        cache_dir=cache_dir,
        from_step=args.from_step,
    )
    step_timings["step2"] = (t2, s2)

    # Step 3: 디스패치·사이징
    step3_data, t3, s3 = run_step3_sizing(
        config_values=country_config.values,
        weather_df=weather_df,
        kosis_dir=kosis_dir,
        step1_data=step1_data,
        step2_data=step2_data,
        cache_dir=cache_dir,
        out_dir=out_dir,
        from_step=args.from_step,
    )
    step_timings["step3"] = (t3, s3)

    # Step 3b: 디스패치 재현 (560건 병렬 디스패치, 15분 시계열 저장 및 재현 점검)
    step3b_data, t3b, s3b = run_step3b_dispatch(
        config_values=country_config.values,
        weather_df=weather_df,
        step1_data=step1_data,
        step2_data=step2_data,
        step3_data=step3_data,
        country_dir=country_dir,
    )
    step_timings["step3b"] = (t3b, s3b)

    # Step 4: 현금흐름·민감도 (차분 점검 포함)
    step4_data, t4, s4 = run_step4_cashflow(
        config_values=country_config.values,
        weather_df=weather_df,
        step1_data=step1_data,
        step2_data=step2_data,
        step3_data=step3_data,
        cache_dir=cache_dir,
        from_step=args.from_step,
        step3b_data=step3b_data,
    )
    step_timings["step4"] = (t4, s4)

    # Step 5: report_data·빌드
    t5, s5 = run_step5_report(
        country_dir=country_dir,
        config_values=country_config.values,
        weather_df=weather_df,
        annual_ghi=annual_ghi,
        run_id=run_id,
        step4_data=step4_data,
        step_timings=step_timings,
    )
    step_timings["step5"] = (t5, s5)

    total_pipe_time = time.perf_counter() - pipe_t0
    print(f"\n[SUCCESS] Completed 5-Step ROI pipeline in {total_pipe_time:.2f}s.")
    print(f"- Output Full CSV: {out_dir / 'results_all.csv'} (Rows: {len(step4_data['df_results'])})")
    print(f"- Energy Comparison CSV: {out_dir / 'energy_comparison.csv'} (Rows: {len(step4_data['df_energy_comp'])})")
    print(f"- Zero Energy Sizing CSV: {out_dir / 'ze_sizing.csv'} (Rows: {len(step4_data['df_ze_sizing'])})")
    print(f"- ZE No Start Constraint CSV: {out_dir / 'ze_no_start_constraint.csv'}")
    print(f"- Summary: {out_dir / 'results_summary.md'}")
    print(f"- Validation: {out_dir / 'validation.md'}")
    print(f"- Report Data: {report_dir / 'report_data.json'}")
    print(f"- HTML Report: {report_dir / 'LG_SC_Korea_ROI_Report.html'}")


if __name__ == "__main__":
    main()
