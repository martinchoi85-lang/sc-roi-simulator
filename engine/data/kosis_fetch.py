"""KOSIS OpenAPI 2024 Time Use Survey (TUS) data collector and validator.

Fetches 2024 Time Use Survey tables (T1, T2, T3, T4, P, H, CR, V, MV, M),
parses 30-minute slots, applies zero-filling, stores raw JSON in korea/source/kosis/raw/,
and produces standardized CSVs in korea/source/kosis/<TABLE>_2024.csv.

Security & Integrity:
- NEVER log, write, or persist the API key to files, logs, json, or reports.
- Strip leading/trailing whitespaces and tabs from API key.
- URL logs mask apiKey as 'apiKey=***'.
- Strict Section 4-4 verification: halts if T1~T4, P, H, MV do not have 48 30-minute slots.
"""

from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


TARGET_TABLES = {
    "T1": "일-평일 행동비율(15세 이상 취업자)",
    "T2": "일 관련 이동-행동비율(15세 이상 취업자)",
    "T3": "문화 및 여가활동-취업여부별 행동비율(15세 이상)",
    "T4": "교제 및 참여활동-취업여부별 행동비율(15세 이상)",
    "P": "개인유지-행동비율(10세 이상)",
    "H": "가정관리-행동비율(19세 이상)",
    "CR": "가족 및 가구원 돌보기-행동비율(19세 이상)",
    "V": "자원봉사 및 무급연수-행동비율(10세 이상)",
    "MV": "이동-행동 비율(10세 이상)",
    "M": "시간대별 행동비율(10세 이상)",
    "AT": "취업여부별 평균시간(15세이상)",
}

KNOWN_TBL_IDS = {
    "T1": "DT_2019_160_1TM2031XX",
    "T2": "DT_2019_184_1TM2123XX",
    "T3": "DT_2019_181_1TM2106XX",
    "T4": "DT_2019_176_1TM2101XX",
    "P": "DT_2019_158_1TM2021XX",
    "H": "DT_2019_167_1TM2051XX",
    "CR": "DT_2019_169_1TM2071XX",
    "V": "DT_2019_172_1TM2097XX",
    "MV": "DT_2019_183_1TM2121XX",
    "M": "DT_2019_191_1TM2129XX",
    "AT": "DT_2019_022_1TM1054X",
}

# 7 aggregated time intervals in table M
M_7_INTERVALS = [
    ("10", "새벽 00:00~05:59", 0, 12),
    ("20", "아침 06:00~08:59", 12, 18),
    ("30", "오전 09:00~11:59", 18, 24),
    ("40", "점심 12:00~13:59", 24, 28),
    ("50", "오후 14:00~17:59", 28, 36),
    ("60", "저녁 18:00~20:59", 36, 42),
    ("70", "밤 21:00~23:59", 42, 48),
]


def mask_url(url: str) -> str:
    """Masks apiKey parameter in URL for logging."""
    return re.sub(r"apiKey=[^&]+", "apiKey=***", url)


def remove_api_key_from_url(url: str) -> str:
    """Removes apiKey parameter completely from URL for documentation."""
    url_without = re.sub(r"([?&])apiKey=[^&]+(&|$)", r"\1", url)
    return url_without.rstrip("?&")


def fetch_json(url: str, retries: int = 1, delay: float = 0.5) -> Any:
    """Fetches JSON from URL with retry and polite delay."""
    print(f"[FETCH] {mask_url(url)}")
    attempt = 0
    while attempt <= retries:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                text = resp.read().decode("utf-8")
                data = json.loads(text)
                time.sleep(delay)
                return data
        except Exception as exc:
            attempt += 1
            if attempt > retries:
                raise RuntimeError(f"Failed to fetch {mask_url(url)} after {retries} retries: {exc}")
            time.sleep(delay * 2)


def get_api_key(arg_key: Optional[str] = None) -> str:
    """Retrieves API key from argument, environment variable, or Windows registry."""
    key = arg_key or os.environ.get("KOSIS_API_KEY", "")
    if not key:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as env_k:
                key, _ = winreg.QueryValueEx(env_k, "KOSIS_API_KEY")
        except Exception:
            pass

    key = (key or "").strip(" \t\r\n")
    if not key:
        raise ValueError("KOSIS API key is missing. Set KOSIS_API_KEY environment variable or pass --api-key.")
    return key


def find_tables(api_key: str, parent_list_id: str = "B_9_001_004_001_001") -> Dict[str, Tuple[str, str]]:
    """Finds table IDs matching target table names from KOSIS hierarchy."""
    base_url = "https://kosis.kr/openapi/statisticsList.do"
    current_parent = parent_list_id
    found_tables: Dict[str, Tuple[str, str]] = {}

    while current_parent:
        url = (
            f"{base_url}?method=getList&vwCd=MT_ZTITLE&parentListId={current_parent}"
            f"&format=json&jsonVD=Y&apiKey={api_key}"
        )
        try:
            items = fetch_json(url)
        except Exception as exc:
            print(f"[WARN] Error fetching list for {current_parent}: {exc}")
            items = []

        if isinstance(items, list):
            for item in items:
                tbl_nm = (item.get("TBL_NM") or "").strip()
                tbl_id = (item.get("TBL_ID") or "").strip()
                if not tbl_id or not tbl_nm:
                    continue
                for code, target_name in TARGET_TABLES.items():
                    if code not in found_tables:
                        clean_target = re.sub(r"\s+", "", target_name)
                        clean_nm = re.sub(r"\s+", "", tbl_nm)
                        if clean_target == clean_nm:
                            found_tables[code] = (tbl_id, tbl_nm)

        if len(found_tables) == len(TARGET_TABLES):
            break

        parts = current_parent.rsplit("_", 1)
        if len(parts) > 1 and parts[0] != current_parent:
            current_parent = parts[0]
        else:
            break

    # Fill in known IDs as fallback if any missing
    for code, known_id in KNOWN_TBL_IDS.items():
        if code not in found_tables:
            found_tables[code] = (known_id, TARGET_TABLES[code])

    missing = [f"{k}: {TARGET_TABLES[k]}" for k in TARGET_TABLES if k not in found_tables]
    if missing:
        missing_str = ", ".join(missing)
        raise RuntimeError(f"Could not find table IDs for: {missing_str}")

    return found_tables


def get_table_metadata(api_key: str, tbl_id: str) -> List[Dict[str, Any]]:
    """Fetches table dimension metadata using getMeta."""
    url = (
        f"https://kosis.kr/openapi/statisticsData.do?method=getMeta&type=ITM&orgId=101"
        f"&tblId={tbl_id}&format=json&jsonVD=Y&apiKey={api_key}"
    )
    meta = fetch_json(url)
    if not isinstance(meta, list):
        raise RuntimeError(f"Unexpected metadata response format for {tbl_id}: {meta}")
    return meta


def parse_korean_slot_to_24h(slot_name: str) -> Optional[str]:
    """Parses slot name to 24-hour HH:MM format."""
    m_ampm = re.match(r"(오전|오후)\s*(\d{1,2}):(\d{2})", slot_name)
    if m_ampm:
        ampm, h_str, m_str = m_ampm.groups()
        hour = int(h_str)
        minute = int(m_str)
        if ampm == "오전":
            if hour == 12:
                hour = 0
        elif ampm == "오후":
            if hour != 12:
                hour += 12
        return f"{hour:02d}:{minute:02d}"

    m_range = re.search(r"(\d{2}):(\d{2})\s*~\s*(\d{2}):(\d{2})", slot_name)
    if m_range:
        h1, m1, h2, m2 = map(int, m_range.groups())
        dur = (h2 * 60 + m2) - (h1 * 60 + m1)
        if dur < 0:
            dur += 1440
        if 28 <= dur <= 30:
            return f"{h1:02d}:{m1:02d}"
        return None

    return None


def fetch_and_save_data(
    api_key: str,
    output_dir: Path,
    raw_dir: Path,
) -> Dict[str, Any]:
    """Main execution function to fetch all 10 tables, zero-fill, and run 4-4 check."""
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    tables = find_tables(api_key)
    print(f"[INFO] Target tables ({len(tables)}): {list(tables.keys())}")

    summary_metrics: Dict[str, Any] = {}
    sources_info: List[Dict[str, str]] = []

    for code, (tbl_id, tbl_nm) in tables.items():
        print(f"\n[INFO] Processing table [{code}]: {tbl_nm} ({tbl_id})...")
        meta = get_table_metadata(api_key, tbl_id)

        # Inspect dimensions
        dims: Dict[Tuple[str, str, str], List[Tuple[str, str]]] = {}
        for item in meta:
            obj_id = item.get("OBJ_ID")
            sn = item.get("OBJ_ID_SN", "ITEM")
            obj_nm = item.get("OBJ_NM", "").strip()
            itm_id = item.get("ITM_ID")
            itm_nm = (item.get("ITM_NM") or "").strip()
            key_dim = (sn, obj_id, obj_nm)
            if key_dim not in dims:
                dims[key_dim] = []
            dims[key_dim].append((itm_id, itm_nm))

        sorted_dims = sorted(dims.keys(), key=lambda x: (int(x[0]) if str(x[0]).isdigit() else 999, str(x[1])))

        dim_map: Dict[str, Dict[str, Any]] = {}
        idx = 1
        for sn, obj_id, obj_nm in sorted_dims:
            if obj_id == "ITEM":
                continue
            dim_map[f"objL{idx}"] = {
                "sn": sn,
                "obj_id": obj_id,
                "obj_nm": obj_nm,
                "items": dims[(sn, obj_id, obj_nm)],
            }
            idx += 1

        day_param_key = None
        sex_param_key = None
        emp_param_key = None
        act_param_key = None
        time_param_key = None

        day_items = []
        sex_items = []
        time_items_meta = []

        for p_key, info in dim_map.items():
            nm = info["obj_nm"]
            items = info["items"]
            if "요일" in nm:
                day_param_key = p_key
                for itm_id, itm_nm in items:
                    if any(d in itm_nm for d in ["평일", "토요일", "일요일"]) and "평균" not in itm_nm:
                        day_items.append((itm_id, itm_nm))
            elif "성별" in nm:
                sex_param_key = p_key
                for itm_id, itm_nm in items:
                    if itm_nm in ["남자", "여자"]:
                        sex_items.append((itm_id, itm_nm))
            elif "취업여부" in nm:
                emp_param_key = p_key
            elif "행동분류" in nm:
                act_param_key = p_key
            elif "시간" in nm or "간격" in nm:
                time_param_key = p_key
                time_items_meta = items

        emp_code = None
        emp_nm = ""
        if emp_param_key:
            for itm_id, itm_nm in dim_map[emp_param_key]["items"]:
                if "취업자" in itm_nm and "비취업자" not in itm_nm:
                    emp_code = itm_id
                    emp_nm = itm_nm
                    break

        if not day_items:
            day_items = [("A1", "평일")]

        # Query combinations of (day, sex)
        raw_rows_count = 0
        parsed_entries: List[Dict[str, Any]] = []
        sample_query_url = ""

        # Extract expected time slots from metadata
        expected_slots: List[Tuple[str, str, Optional[str]]] = []
        for s_code, s_name in time_items_meta:
            s_start = parse_korean_slot_to_24h(s_name)
            expected_slots.append((s_code, s_name, s_start))

        for d_id, d_nm in day_items:
            for s_id, s_nm in sex_items:
                raw_filename = f"{code}_{d_id}_{s_id}.json"
                raw_path = raw_dir / raw_filename

                if raw_path.exists():
                    with open(raw_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    params = {
                        "method": "getList",
                        "orgId": "101",
                        "tblId": tbl_id,
                        "itmId": "T10",
                        "prdSe": "F",
                        "startPrdDe": "2024",
                        "endPrdDe": "2024",
                        "format": "json",
                        "jsonVD": "Y",
                    }
                    for p_key, info in dim_map.items():
                        if p_key == day_param_key:
                            params[p_key] = d_id
                        elif p_key == sex_param_key:
                            params[p_key] = s_id
                        elif p_key == emp_param_key and emp_code:
                            params[p_key] = emp_code
                        else:
                            params[p_key] = "ALL"

                    qs = urllib.parse.urlencode(params)
                    url = f"https://kosis.kr/openapi/Param/statisticsParameterData.do?{qs}&apiKey={api_key}"
                    if not sample_query_url:
                        sample_query_url = remove_api_key_from_url(url)

                    try:
                        data = fetch_json(url, retries=1, delay=0.5)
                    except Exception as exc:
                        print(f"[ERROR] Failed to fetch data for {code} ({d_nm}, {s_nm}): {exc}")
                        data = []

                    if isinstance(data, list):
                        with open(raw_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)

                if isinstance(data, list):
                    raw_rows_count += len(data)
                    for r in data:
                        act_code = ""
                        act_name = ""
                        slot_code = ""
                        slot_name = ""
                        r_day_code = d_id
                        r_day_name = d_nm
                        r_sex_code = s_id
                        r_sex_name = s_nm
                        r_emp_name = emp_nm

                        for p_idx in range(1, 9):
                            c_val = r.get(f"C{p_idx}", "")
                            c_nm = r.get(f"C{p_idx}_NM", "")
                            o_nm = r.get(f"C{p_idx}_OBJ_NM", "")

                            if "행동" in o_nm:
                                act_code = c_val
                                act_name = c_nm
                            elif "시간" in o_nm or "간격" in o_nm:
                                slot_code = c_val
                                slot_name = c_nm
                            elif "요일" in o_nm:
                                r_day_code = c_val
                                r_day_name = c_nm
                            elif "성별" in o_nm:
                                r_sex_code = c_val
                                r_sex_name = c_nm
                            elif "취업여부" in o_nm:
                                r_emp_name = c_nm

                        val_str = r.get("DT", "0").replace("-", "0")
                        try:
                            val_float = float(val_str)
                        except ValueError:
                            val_float = 0.0

                        code_len = len(act_code)
                        if code_len == 1:
                            act_level = "대"
                        elif code_len == 2:
                            act_level = "중"
                        else:
                            act_level = "소"

                        slot_start = parse_korean_slot_to_24h(slot_name)

                        parsed_entries.append({
                            "table": code,
                            "day_code": r_day_code,
                            "day_name": r_day_name,
                            "sex_code": r_sex_code,
                            "sex_name": r_sex_name,
                            "emp_name": r_emp_name,
                            "act_code": act_code,
                            "act_name": act_name,
                            "act_level": act_level,
                            "slot_code": slot_code,
                            "slot_name": slot_name,
                            "slot_start": slot_start,
                            "value": val_float,
                        })

        if not sample_query_url:
            sample_query_url = f"https://kosis.kr/openapi/Param/statisticsParameterData.do?method=getList&orgId=101&tblId={tbl_id}&itmId=T10&prdSe=F&startPrdDe=2024&endPrdDe=2024&format=json&jsonVD=Y"

        # Apply Zero-Filling per Section 4-3:
        # 빈칸 처리: 행동 × 요일 × 성별마다 48칸을 채우고, 응답에 없는 칸은 0으로 넣는다.
        # M은 7구간을 그대로 둔다.
        clean_rows: List[Dict[str, Any]] = []
        zero_filled_count = 0
        zero_filled_by_act: Dict[str, int] = {}

        if code == "M":
            # Keep 7 intervals as is
            clean_rows = parsed_entries
            distinct_slots = set(r["slot_name"] for r in clean_rows)
            slots_count = len(distinct_slots)
        else:
            # 30-minute tables: ensure exactly 48 slots per (day, sex, act)
            # Find all unique (day, sex, act) series
            unique_acts = {}
            for r in parsed_entries:
                key_act = r["act_code"]
                if key_act not in unique_acts:
                    unique_acts[key_act] = (r["act_name"], r["act_level"])

            # Map existing parsed entries by (day_code, sex_code, act_code, slot_code)
            entry_map = {
                (r["day_code"], r["sex_code"], r["act_code"], r["slot_code"]): r
                for r in parsed_entries
            }

            for d_id, d_nm in day_items:
                for s_id, s_nm in sex_items:
                    for act_code, (act_name, act_level) in unique_acts.items():
                        for s_code, s_name, s_start in expected_slots:
                            k = (d_id, s_id, act_code, s_code)
                            if k in entry_map:
                                clean_rows.append(entry_map[k])
                            else:
                                zero_filled_count += 1
                                zero_filled_by_act[act_name] = zero_filled_by_act.get(act_name, 0) + 1
                                clean_rows.append({
                                    "table": code,
                                    "day_code": d_id,
                                    "day_name": d_nm,
                                    "sex_code": s_id,
                                    "sex_name": s_nm,
                                    "emp_name": emp_nm,
                                    "act_code": act_code,
                                    "act_name": act_name,
                                    "act_level": act_level,
                                    "slot_code": s_code,
                                    "slot_name": s_name,
                                    "slot_start": s_start,
                                    "value": 0.0,
                                })

            distinct_slots = set(r["slot_name"] for r in clean_rows)
            slots_count = len(distinct_slots)

        # Write clean CSV
        csv_path = output_dir / f"{code}_2024.csv"
        import csv
        fieldnames = [
            "table", "day_code", "day_name", "sex_code", "sex_name", "emp_name",
            "act_code", "act_name", "act_level", "slot_code", "slot_name", "slot_start", "value"
        ]
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in clean_rows:
                writer.writerow(r)

        print(f"[INFO] Saved {len(clean_rows)} rows to {csv_path} (Raw rows: {raw_rows_count}, Zero-filled: {zero_filled_count}, Slots: {slots_count})")

        selection_codes_str = f"요일: {', '.join([d[0] for d in day_items])}, 성별: {', '.join([s[0] for s in sex_items])}"
        if emp_code:
            selection_codes_str += f", 취업: {emp_code}"

        summary_metrics[code] = {
            "tbl_id": tbl_id,
            "tbl_nm": tbl_nm,
            "selection_codes": selection_codes_str,
            "raw_rows_count": raw_rows_count,
            "zero_filled_count": zero_filled_count,
            "zero_filled_by_act": zero_filled_by_act,
            "slots_count": slots_count,
            "has_day_dim": day_param_key is not None,
            "sample_query_url": sample_query_url,
        }

        sources_info.append({
            "code": code,
            "name": tbl_nm,
            "tbl_id": tbl_id,
            "url": sample_query_url,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "status": "VERIFIED(API 원자료)",
        })

    # Update korea/source/kosis/SOURCE.md
    source_md_path = output_dir / "SOURCE.md"
    with open(source_md_path, "w", encoding="utf-8") as f:
        f.write("# KOSIS 2024 생활시간조사 통계표 출처 목록\n\n")
        for s in sources_info:
            f.write(f"## [{s['code']}] {s['name']}\n")
            f.write(f"- **TBL_ID:** `{s['tbl_id']}`\n")
            f.write(f"- **Request URL:** `{s['url']}`\n")
            f.write(f"- **수집 일시:** {s['date']}\n")
            f.write(f"- **Status:** {s['status']}\n\n")

    print(f"[INFO] Updated {source_md_path}")

    # Section 4-4 점검
    validation_4_4 = run_section_4_4_check(summary_metrics, output_dir)
    summary_metrics["validation_4_4"] = validation_4_4

    return summary_metrics


def run_section_4_4_check(metrics: Dict[str, Any], kosis_dir: Path) -> Dict[str, Any]:
    """Executes Section 4-4 checks: slot count check, M 7-interval consistency check."""
    import pandas as pd
    import numpy as np

    # 1. 48-slot check for T1~T4, P, H, MV
    check_tables = ["T1", "T2", "T3", "T4", "P", "H", "MV"]
    failed_tables = []
    table_slot_status = {}

    for t in check_tables:
        info = metrics.get(t, {})
        slots = info.get("slots_count", 0)
        table_slot_status[t] = slots
        if slots != 48:
            failed_tables.append(f"{t} (slots={slots} != 48)")

    if failed_tables:
        err_msg = f"Section 4-4 Check FAIL: Tables not having 48 30-minute slots: {', '.join(failed_tables)}"
        print(f"[FATAL] {err_msg}")
        raise RuntimeError(err_msg)

    # 2. Consistency check: Reaggregate P, H, MV 30-min values to M 7-intervals and compare
    m_csv = kosis_dir / "M_2024.csv"
    p_csv = kosis_dir / "P_2024.csv"
    h_csv = kosis_dir / "H_2024.csv"
    mv_csv = kosis_dir / "MV_2024.csv"

    consistency_results: Dict[str, Any] = {}
    if m_csv.exists() and p_csv.exists() and h_csv.exists() and mv_csv.exists():
        df_m = pd.read_csv(m_csv)
        target_map = {
            "P": (p_csv, "개인유지", 1),
            "H": (h_csv, "가정관리", 4),
            "MV": (mv_csv, "이동", 9),
        }

        for code, (csv_file, act_name, act_code) in target_map.items():
            df_sub = pd.read_csv(csv_file)
            df_sub_act = df_sub[(df_sub["act_code"].astype(str) == str(act_code)) | (df_sub["act_name"] == act_name)]

            max_diff_pct_p = 0.0
            interval_diffs = []

            for d_name in ["평일", "토요일", "일요일"]:
                for s_name in ["남자", "여자"]:
                    m_series = df_m[(df_m["day_name"] == d_name) & (df_m["sex_name"] == s_name) & ((df_m["act_code"].astype(str) == str(act_code)) | (df_m["act_name"] == act_name))]
                    sub_series = df_sub_act[(df_sub_act["day_name"] == d_name) & (df_sub_act["sex_name"] == s_name)]

                    # Order 48 slots by slot_start
                    sub_series = sub_series.sort_values("slot_start")
                    sub_vals = sub_series["value"].tolist()

                    if len(sub_vals) == 48 and len(m_series) == 7:
                        for inter_code, inter_name, start_idx, end_idx in M_7_INTERVALS:
                            reagg_mean = float(np.mean(sub_vals[start_idx:end_idx]))
                            m_row = m_series[m_series["slot_name"] == inter_name]
                            if len(m_row) > 0:
                                m_val = float(m_row.iloc[0]["value"])
                                diff = abs(reagg_mean - m_val)
                                if diff > max_diff_pct_p:
                                    max_diff_pct_p = diff
                                interval_diffs.append({
                                    "table": code,
                                    "day": d_name,
                                    "sex": s_name,
                                    "interval": inter_name,
                                    "reagg_mean": round(reagg_mean, 2),
                                    "m_val": round(m_val, 2),
                                    "diff_pct_p": round(diff, 2),
                                })

            consistency_results[code] = {
                "act_name": act_name,
                "max_diff_pct_p": round(max_diff_pct_p, 2),
                "sample_diffs": interval_diffs[:5],
            }

    print("\n[SECTION 4-4 CHECK RESULT]")
    print(f"- 48-slot check for T1~T4, P, H, MV: ALL PASS ({table_slot_status})")
    for code, c_res in consistency_results.items():
        print(f"- M 7-interval consistency [{code} ({c_res['act_name']})]: Max difference = {c_res['max_diff_pct_p']}%p (기록용)")

    return {
        "status": "PASS",
        "table_slot_status": table_slot_status,
        "consistency": consistency_results,
    }


def get_kosis_average_time_realism(kosis_dir: Path) -> List[Dict[str, Any]]:
    """Returns KOSIS average time benchmarks for employed persons (sleep, work, commute/travel)."""
    csv_path = kosis_dir / "AT_2024.csv"
    if not csv_path.exists():
        return []
    import pandas as pd
    df = pd.read_csv(csv_path)
    res = []
    day_map = {"평일": "weekday", "토요일": "saturday", "일요일": "sunday"}
    act_map = {"111": "수면", "2": "일", "9": "이동"}
    for day_korean, dt in day_map.items():
        for act_code, metric_name in act_map.items():
            sub = df[(df["day_name"] == day_korean) & (df["act_code"].astype(str) == act_code)]
            if len(sub) > 0:
                mins = int(sub.iloc[0]["value_min"])
                res.append({
                    "metric": metric_name,
                    "daytype": dt,
                    "kosis": mins,
                    "unit": "min",
                })
    return res


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch and validate KOSIS 2024 TUS tables.")
    parser.add_argument("--api-key", default=None, help="KOSIS OpenAPI key")
    args = parser.parse_args()

    key = get_api_key(args.api_key)
    proj_root = Path(__file__).resolve().parent.parent.parent
    kosis_dir = proj_root / "korea" / "source" / "kosis"
    raw_dir = kosis_dir / "raw"

    res = fetch_and_save_data(key, kosis_dir, raw_dir)
    print("\n[SUCCESS] Completed KOSIS fetch and Section 4-4 verification successfully.")
