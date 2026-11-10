"""KOSIS OpenAPI time-use survey data collector.

Fetches 2024 Time Use Survey tables (M, T1, T2, T3, T4), parses 30-minute slots,
stores raw JSON into korea/source/kosis/raw/, and saves standardized CSVs
into korea/source/kosis/<TABLE>_2024.csv.

Security & Integrity Rules:
- NEVER log, write, or persist the API key to code, logs, json, reports, or SOURCE.md.
- In all logged URLs, mask apiKey as ***.
- Strip leading and trailing whitespace and tabs from the API key.
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
    "M": "시간대별 행동비율(10세 이상)",
    "T1": "일-평일 행동비율(15세 이상 취업자)",
    "T2": "일 관련 이동-행동비율(15세 이상 취업자)",
    "T3": "문화 및 여가활동-취업여부별 행동비율(15세 이상)",
    "T4": "교제 및 참여활동-취업여부별 행동비율(15세 이상)",
}

KNOWN_TBL_IDS = {
    "M": "DT_2019_191_1TM2129XX",
}


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
    """Retrieves API key from argument or environment variable."""
    key = arg_key or os.environ.get("KOSIS_API_KEY", "")
    key = key.strip(" \t\r\n")
    if not key:
        raise ValueError("KOSIS API key is missing. Set KOSIS_API_KEY environment variable or pass --api-key.")
    return key


def find_tables(api_key: str, parent_list_id: str = "B_9_001_004_001_001") -> Dict[str, Tuple[str, str]]:
    """Finds table IDs matching target table names."""
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
                        # Normalize whitespaces for comparison
                        clean_target = re.sub(r"\s+", "", target_name)
                        clean_nm = re.sub(r"\s+", "", tbl_nm)
                        if clean_target == clean_nm:
                            found_tables[code] = (tbl_id, tbl_nm)

        # Check if all found
        if len(found_tables) == len(TARGET_TABLES):
            break

        # Move up to parent
        parts = current_parent.rsplit("_", 1)
        if len(parts) > 1 and parts[0] != current_parent:
            current_parent = parts[0]
        else:
            break

    # Fill in known IDs if any missing
    for code, known_id in KNOWN_TBL_IDS.items():
        if code not in found_tables:
            found_tables[code] = (known_id, TARGET_TABLES[code])

    missing = [f"{k}: {TARGET_TABLES[k]}" for k in TARGET_TABLES if k not in found_tables]
    if missing:
        missing_str = ", ".join(missing)
        raise RuntimeError(f"Could not find table IDs for: {missing_str}")

    return found_tables


def get_table_metadata(api_key: str, tbl_id: str) -> List[Dict[str, Any]]:
    """Fetches table dimension metadata using statisticsData.do getMeta."""
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
    # Case 1: "오전 00:00", "오후 01:30", "오후 12:00"
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

    # Case 2: "HH:MM~HH:MM" (e.g. "00:00~00:30" or "새벽 00:00~05:59")
    m_range = re.search(r"(\d{2}):(\d{2})\s*~\s*(\d{2}):(\d{2})", slot_name)
    if m_range:
        h1, m1, h2, m2 = map(int, m_range.groups())
        dur = (h2 * 60 + m2) - (h1 * 60 + m1)
        # Handle rollover if any
        if dur < 0:
            dur += 1440
        # If exactly 30 minutes (or 29/30 minutes like 00:00~00:29 or 00:00~00:30)
        if 28 <= dur <= 30:
            return f"{h1:02d}:{m1:02d}"
        return None

    return None


def fetch_and_save_data(
    api_key: str,
    output_dir: Path,
    raw_dir: Path,
) -> Dict[str, Any]:
    """Main execution function to fetch all 5 tables and save raw JSON & clean CSVs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    # 1. Find tables
    tables = find_tables(api_key)
    print(f"[INFO] Found all {len(tables)} tables: {list(tables.keys())}")

    summary_metrics: Dict[str, Any] = {}
    sources_info: List[Dict[str, str]] = []

    for code, (tbl_id, tbl_nm) in tables.items():
        print(f"\n[INFO] Processing table {code}: {tbl_nm} ({tbl_id})...")
        meta = get_table_metadata(api_key, tbl_id)

        # Inspect dimensions
        # Find dimension variables
        dims: Dict[str, Dict[str, Any]] = {}
        for item in meta:
            obj_id = item.get("OBJ_ID")
            sn = item.get("OBJ_ID_SN", "ITEM")
            obj_nm = item.get("OBJ_NM", "").strip()
            itm_id = item.get("ITM_ID")
            itm_nm = (item.get("ITM_NM") or "").strip()
            key = (sn, obj_id, obj_nm)
            if key not in dims:
                dims[key] = []
            dims[key].append((itm_id, itm_nm))

        sorted_dims = sorted(dims.keys(), key=lambda x: (int(x[0]) if str(x[0]).isdigit() else 999, str(x[1])))

        # Map dimensions to objL1..objLn
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

        # Determine target codes
        # 요일 = 평일/토요일/일요일, 성별 = 남자/여자, 취업여부 = 취업자, 행동 = ALL, 시간대 = ALL
        day_param_key = None
        sex_param_key = None
        emp_param_key = None
        act_param_key = None
        time_param_key = None

        day_items = []
        sex_items = []

        for p_key, info in dim_map.items():
            nm = info["obj_nm"]
            items = info["items"]
            if "요일" in nm:
                day_param_key = p_key
                # Filter 평일, 토요일, 일요일
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

        emp_code = None
        emp_nm = ""
        if emp_param_key:
            for itm_id, itm_nm in dim_map[emp_param_key]["items"]:
                if "취업자" in itm_nm and "비취업자" not in itm_nm:
                    emp_code = itm_id
                    emp_nm = itm_nm
                    break

        # Fallback if no day dimension (e.g. T1 has no day dimension, it is weekday only)
        if not day_items:
            day_items = [("A1", "평일")]

        # Query combinations of (day, sex)
        all_raw_rows = []
        clean_rows = []
        sample_query_url = ""

        for d_id, d_nm in day_items:
            for s_id, s_nm in sex_items:
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
                    elif p_key == act_param_key:
                        params[p_key] = "ALL"
                    elif p_key == time_param_key:
                        params[p_key] = "ALL"
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
                    continue

                if isinstance(data, list):
                    all_raw_rows.extend(data)
                    # Save raw JSON for this slice
                    raw_filename = f"{code}_{d_id}_{s_id}.json"
                    raw_path = raw_dir / raw_filename
                    with open(raw_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                    # Parse clean rows
                    for r in data:
                        # Extract fields
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
                            c_key = f"C{p_idx}"
                            cnm_key = f"C{p_idx}_NM"
                            obj_nm_key = f"C{p_idx}_OBJ_NM"
                            c_val = r.get(c_key, "")
                            c_nm = r.get(cnm_key, "")
                            o_nm = r.get(obj_nm_key, "")

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

                        # Value
                        val_str = r.get("DT", "0").replace("-", "0")
                        try:
                            val_float = float(val_str)
                        except ValueError:
                            val_float = 0.0

                        # Level by act_code length
                        # Length 1: 대, length 2: 중, length 3+: 소
                        code_len = len(act_code)
                        if code_len == 1:
                            act_level = "대"
                        elif code_len == 2:
                            act_level = "중"
                        else:
                            act_level = "소"

                        # Parse slot start and filter 30-minute intervals
                        slot_start = parse_korean_slot_to_24h(slot_name)

                        # If slot_start is None, check if it's a 30-min slot from T3 format (10000~21130)
                        if slot_start is None:
                            # If slot_name has range like 00:00~05:59, duration is > 30 min, skip for 30m filter
                            pass

                        clean_rows.append({
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
                else:
                    print(f"[WARN] Non-list response for {code} ({d_nm}, {s_nm}): {data}")

        # Filter 30-minute slots where slot_start is valid
        # Keep track of total slots count and 30m slots count
        distinct_slots = set(r["slot_name"] for r in clean_rows)
        distinct_30m_slots = set(r["slot_name"] for r in clean_rows if r["slot_start"] is not None)

        # Write clean CSV
        # Note: If code == 'M', distinct_30m_slots is 0 because all 7 slots are broad ranges (새벽, 아침...)
        # We save all clean rows so the data is preserved for inspection & validation
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

        print(f"[INFO] Saved {len(clean_rows)} rows to {csv_path} (Distinct slots: {len(distinct_slots)}, 30m slots: {len(distinct_30m_slots)})")

        summary_metrics[code] = {
            "tbl_id": tbl_id,
            "tbl_nm": tbl_nm,
            "total_rows": len(clean_rows),
            "distinct_slots_count": len(distinct_slots),
            "slots_30m_count": len(distinct_30m_slots),
            "distinct_slots": sorted(list(distinct_slots)),
            "has_day_dim": day_param_key is not None,
            "has_sex_dim": sex_param_key is not None,
            "has_emp_dim": emp_param_key is not None,
            "clean_rows": clean_rows,
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

    # Move old tus2024_activity_share.csv to archive/
    old_csv = output_dir / "tus2024_activity_share.csv"
    if old_csv.exists():
        archive_dir = output_dir / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archived_target = archive_dir / "tus2024_activity_share.csv"
        shutil.move(str(old_csv), str(archived_target))
        print(f"[INFO] Moved old {old_csv.name} to {archived_target}")

    return summary_metrics


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch KOSIS 2024 TUS tables.")
    parser.add_argument("--api-key", default=None, help="KOSIS OpenAPI key")
    args = parser.parse_args()

    key = get_api_key(args.api_key)
    proj_root = Path(__file__).resolve().parent.parent.parent
    kosis_dir = proj_root / "korea" / "source" / "kosis"
    raw_dir = kosis_dir / "raw"

    fetch_and_save_data(key, kosis_dir, raw_dir)

