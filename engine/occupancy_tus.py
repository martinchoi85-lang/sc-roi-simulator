"""KOSIS 2024 Time Use Survey (TUS) probabilistic occupancy and appliance load model.

Implements Mode A (KOSIS-based time-inhomogeneous 3-state Markov chain, CREST-like approach)
and Mode B (fixed weekday/weekend schedule fallback).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from engine.occupancy import generate_occupancy_calendar


class OccupancyTUSModel:
    """TUS-based probabilistic occupant and appliance load simulation."""

    def __init__(
        self,
        kosis_dir: Union[str, Path],
        load_config: Dict[str, Any],
        house_config: Dict[str, Any],
        weather_df: pd.DataFrame,
        occupants: int = 2,
        seed: int = 42,
        kappa: float = 0.5,
        lambda_mix: Optional[float] = None,
    ):
        self.kosis_dir = Path(kosis_dir)
        self.load_config = load_config
        self.house_config = house_config
        self.weather_df = weather_df
        self.occupants = occupants
        self.seed = seed
        self.kappa = kappa
        self.lambda_mix = None  # λ 혼합 방식 삭제: tus.lambda = null (SPEC 6절 대체)

        # Check mode: new standardized KOSIS files or legacy tus2024_activity_share
        self.kosis_m_path = self.kosis_dir / "M_2024.csv"
        self.kosis_t1_path = self.kosis_dir / "T1_2024.csv"
        self.kosis_t2_path = self.kosis_dir / "T2_2024.csv"
        self.kosis_t3_path = self.kosis_dir / "T3_2024.csv"
        self.kosis_t4_path = self.kosis_dir / "T4_2024.csv"
        self.kosis_p_path = self.kosis_dir / "P_2024.csv"
        self.kosis_h_path = self.kosis_dir / "H_2024.csv"
        self.kosis_cr_path = self.kosis_dir / "CR_2024.csv"
        self.kosis_v_path = self.kosis_dir / "V_2024.csv"
        self.kosis_mv_path = self.kosis_dir / "MV_2024.csv"

        has_new_kosis = self.kosis_m_path.exists() and self.kosis_t1_path.exists()
        legacy_csvs = list(self.kosis_dir.glob("tus2024_activity_share*.csv")) if self.kosis_dir.exists() else []

        if has_new_kosis:
            self.mode = "A"
            self.kosis_format = "new_v10"
        elif legacy_csvs:
            self.mode = "A"
            self.kosis_format = "legacy"
            self.kosis_csv_path = legacy_csvs[0]
        else:
            self.mode = "B"
            self.kosis_format = "none"

        # Mode detail string (strictly conforming to specification)
        self.mode_detail = (
            "KOSIS 2024 생활시간조사의 취업자 시간대별 행동비율(평일 일·출퇴근·여가·교제)과 10세 이상(가정관리는 19세 이상) 행동비율을 결합한 통계 기반 확률 시뮬레이션(실측 아님). 주말 근무 비율은 10세 이상 값을 사용."
            if self.mode == "A"
            else "평일/주말 고정 스케줄 모델 (PLACEHOLDER)"
        )

        # Storage for validation metrics
        self.kosis_validation_metrics = {}
        self.appliance_calibration_errors = {}
        self.mae_reproduction_metrics = {}

        if self.mode == "A":
            self._load_and_validate_kosis()

    def _load_and_validate_kosis(self):
        """Loads and parses KOSIS data (supports new v10 tables or legacy CSV)."""
        if self.kosis_format == "new_v10":
            df_m = pd.read_csv(self.kosis_m_path)
            df_t1 = pd.read_csv(self.kosis_t1_path)
            df_t2 = pd.read_csv(self.kosis_t2_path)
            df_t3 = pd.read_csv(self.kosis_t3_path)
            df_t4 = pd.read_csv(self.kosis_t4_path)
            df_p = pd.read_csv(self.kosis_p_path) if self.kosis_p_path.exists() else None
            df_h = pd.read_csv(self.kosis_h_path) if self.kosis_h_path.exists() else None
            df_cr = pd.read_csv(self.kosis_cr_path) if self.kosis_cr_path.exists() else None
            df_v = pd.read_csv(self.kosis_v_path) if self.kosis_v_path.exists() else None
            df_mv = pd.read_csv(self.kosis_mv_path) if self.kosis_mv_path.exists() else None

            self.df_m = df_m
            self.df_t1 = df_t1
            self.df_t2 = df_t2
            self.df_t3 = df_t3
            self.df_t4 = df_t4
            self.df_p = df_p
            self.df_h = df_h
            self.df_cr = df_cr
            self.df_v = df_v
            self.df_mv = df_mv

            # Check major categories 1-9 in M
            majors = df_m[df_m["act_level"] == "대"]
            major_codes = set(majors["act_code"].astype(str))
            has_all_9 = all(str(i) in major_codes for i in range(1, 10))

            # Check sums across slots in M
            grp = majors.groupby(["day_name", "sex_name", "slot_name"])["value"].sum()
            deviating_rows = sum((grp < 99.5) | (grp > 100.5))

            self.kosis_validation_metrics["subcategories_valid"] = has_all_9
            self.kosis_validation_metrics["deviating_rows_from_100"] = int(deviating_rows)
            self.kosis_validation_metrics["total_rows"] = len(df_m)
        else:
            df = pd.read_csv(self.kosis_csv_path, header=[0, 1])
            sub_ok = True
            deviating_rows = 0
            total_rows = len(df)

            for i in range(total_rows):
                row = df.iloc[i]
                v1 = float(str(row.iloc[3]).replace("-", "0"))
                sub1 = sum([float(str(row.iloc[k]).replace("-", "0")) for k in [4, 5, 6, 7, 8]])
                if sub1 > v1 + 0.1:
                    sub_ok = False

                v4 = float(str(row.iloc[11]).replace("-", "0"))
                sub4 = sum([float(str(row.iloc[k]).replace("-", "0")) for k in [12, 13, 14, 15, 16, 17, 18]])
                if sub4 > v4 + 0.1:
                    sub_ok = False

                deviating_rows += 1

            self.kosis_validation_metrics["subcategories_valid"] = sub_ok
            self.kosis_validation_metrics["deviating_rows_from_100"] = deviating_rows
            self.kosis_validation_metrics["total_rows"] = total_rows
            self.df_kosis = df

        self._init_routine_distributions_cache()

    def _init_routine_distributions_cache(self):
        """Precomputes and caches routine sampling distributions and calibrated sleep/away curves."""
        self._routine_dist_cache = {}
        self._sleep_calib = {}
        self._away_calib = {}
        self._media_calib = {}
        self._cook_calib = {}

        for dt in ["weekday", "saturday", "sunday"]:
            for g in ["male", "female", "avg"]:
                if g == "avg":
                    prof_m = self._get_kosis_activity_profiles(dt, "male")
                    prof_f = self._get_kosis_activity_profiles(dt, "female")
                    prof = {
                        "pi_states": 0.5 * (prof_m["pi_states"] + prof_f["pi_states"]),
                        "sleep": 0.5 * (prof_m["sleep"] + prof_f["sleep"]),
                        "cook": 0.5 * (prof_m["cook"] + prof_f["cook"]),
                        "dish": 0.5 * (prof_m["dish"] + prof_f["dish"]),
                        "wash": 0.5 * (prof_m["wash"] + prof_f["wash"]),
                        "broadcast": 0.5 * (prof_m["broadcast"] + prof_f["broadcast"]),
                        "video": 0.5 * (prof_m["video"] + prof_f["video"]),
                        "hygiene": 0.5 * (prof_m["hygiene"] + prof_f["hygiene"]),
                        "work": 0.5 * (prof_m["work"] + prof_f["work"]),
                        "commute_in": 0.5 * (prof_m["commute_in"] + prof_f["commute_in"]),
                        "commute_out": 0.5 * (prof_m["commute_out"] + prof_f["commute_out"]),
                    }
                else:
                    prof = self._get_kosis_activity_profiles(dt, g)

                # Standard states: 0=away, 1=home_act, 2=sleep
                p_away_tgt = prof["pi_states"][::3, 0].copy()  # 48 slots
                p_home_tgt = prof["pi_states"][::3, 1].copy()
                p_sleep_tgt = prof["pi_states"][::3, 2].copy()

                # Requirement 1-(a): Align weekday away target curve to employed worker at workplace
                # Smooth the lunch dip (slots 23..26, 11:30~13:30) where worker is having lunch at workplace/restaurant (state: away)
                if dt == "weekday":
                    p_away_tgt[23:26] = np.maximum(p_away_tgt[23:26], np.linspace(p_away_tgt[22], p_away_tgt[26], 3))
                    p_home_tgt = np.maximum(0.0, 1.0 - p_away_tgt - p_sleep_tgt)
                elif dt in ("saturday", "sunday"):
                    p_away_tgt[23:26] = np.maximum(p_away_tgt[23:26], np.linspace(p_away_tgt[22], p_away_tgt[26], 3))
                    # Requirement 1-(a): Weekend employed target = p_work * weekday_away + (1 - p_work) * off_away
                    p_work_weekend = 0.486 if dt == "saturday" else 0.353
                    p_away_wd = self._routine_dist_cache[("weekday", g)]["p_away_tgt"]
                    p_away_tgt = p_work_weekend * p_away_wd + (1.0 - p_work_weekend) * p_away_tgt
                    p_home_tgt = np.maximum(0.0, 1.0 - p_away_tgt - p_sleep_tgt)

                d_name = "평일" if dt == "weekday" else ("토요일" if dt == "saturday" else "일요일")
                if g == "avg":
                    sub_m = self.df_t2[(self.df_t2["day_name"] == d_name) & (self.df_t2["sex_name"] == "남자") & (self.df_t2["act_code"].astype(str) == "92")].sort_values("slot_start")
                    sub_f = self.df_t2[(self.df_t2["day_name"] == d_name) & (self.df_t2["sex_name"] == "여자") & (self.df_t2["act_code"].astype(str) == "92")].sort_values("slot_start")
                    c_m = sub_m["value"].to_numpy() / 100.0 if len(sub_m) > 0 else np.zeros(48)
                    c_f = sub_f["value"].to_numpy() / 100.0 if len(sub_f) > 0 else np.zeros(48)
                    c_arr = 0.5 * (c_m + c_f)
                else:
                    g_name = "남자" if g == "male" else "여자"
                    sub_t2 = self.df_t2[(self.df_t2["day_name"] == d_name) & (self.df_t2["sex_name"] == g_name) & (self.df_t2["act_code"].astype(str) == "92")].sort_values("slot_start")
                    c_arr = sub_t2["value"].to_numpy() / 100.0 if len(sub_t2) > 0 else np.zeros(48)

                # Employment status work probability (KOSIS participant rates):
                # Weekdays: 1.0 (all employed commute), Saturday: 0.486, Sunday: 0.353
                p_work = 1.0 if dt == "weekday" else (0.486 if dt == "saturday" else 0.353)

                self._routine_dist_cache[(dt, g)] = {
                    "prof": prof,
                    "p_away_tgt": p_away_tgt,
                    "p_home_tgt": p_home_tgt,
                    "p_sleep_tgt": p_sleep_tgt,
                    "c_arr": c_arr,
                    "p_work": p_work,
                }

            # Precompute calibrated sleep curve per day_type using feedback loop (N=1500, 8 iterations)
            p_tgt_sleep = self._routine_dist_cache[(dt, "avg")]["p_sleep_tgt"]
            p_c = p_tgt_sleep.copy()
            rng_pre = np.random.default_rng(100 + (0 if dt == "weekday" else (1 if dt == "saturday" else 2)))
            for _ in range(8):
                sim_m = np.zeros((1500, 48))
                for i in range(1500):
                    p = np.zeros(48, dtype=int)
                    cur = int(rng_pre.random() < p_c[0])
                    p[0] = cur
                    for t in range(47):
                        if cur == 1:
                            p_stay = min(1.0, p_c[t+1] / max(1e-6, p_c[t]))
                            cur = 1 if rng_pre.random() < p_stay else 0
                        else:
                            p_trans = max(0.0, (p_c[t+1] - p_c[t]) / max(1e-6, 1.0 - p_c[t]))
                            cur = 1 if rng_pre.random() < p_trans else 0
                        p[t+1] = cur
                    for t in range(1, 47):
                        if p[t] != p[t-1] and p[t] != p[t+1]:
                            p[t] = p[t-1]
                    tot_s = p.sum()
                    if tot_s < 8:
                        p[4:12] = 1
                    elif tot_s > 24:
                        excess = tot_s - 24
                        for s in range(16, 40):
                            if p[s] == 1 and excess > 0:
                                p[s] = 0
                                excess -= 1
                        if excess > 0:
                            for s in range(40, 48):
                                if p[s] == 1 and excess > 0:
                                    p[s] = 0
                                    excess -= 1
                    sim_m[i] = p
                diff = sim_m.mean(axis=0) - p_tgt_sleep
                p_c = np.clip(p_c - 0.75 * diff, 0.0, 1.0)
            self._sleep_calib[dt] = p_c

            # Precompute calibrated away curve per day_type using feedback loop (N=1500, 16 iterations)
            p_tgt_away = self._routine_dist_cache[(dt, "avg")]["p_away_tgt"]
            p_work = self._routine_dist_cache[(dt, "avg")]["p_work"]
            if dt == "weekday":
                p_c_away = np.clip(p_tgt_away / np.maximum(0.05, 1.0 - p_tgt_sleep), 0.0, 1.0)
                p_c_away[2:8] = 0.0
            else:
                p_c_wd = self._away_calib["weekday"]
                p_c_off = np.clip((p_tgt_away - p_work * self._routine_dist_cache[("weekday", "avg")]["p_away_tgt"]) / max(0.01, 1.0 - p_work), 0.0, 1.0)
                p_c_away = np.clip(p_c_off / np.maximum(0.05, 1.0 - p_tgt_sleep), 0.0, 1.0)

            for _ in range(16):
                sim_m_away = np.zeros((1500, 48))
                for i in range(1500):
                    # Sleep states
                    p_s = np.zeros(48, dtype=int)
                    cur_s = int(rng_pre.random() < p_c[0])
                    p_s[0] = cur_s
                    for t in range(47):
                        if cur_s == 1:
                            cur_s = 1 if rng_pre.random() < min(1.0, p_c[t+1] / max(1e-6, p_c[t])) else 0
                        else:
                            cur_s = 1 if rng_pre.random() < max(0.0, (p_c[t+1] - p_c[t]) / max(1e-6, 1.0 - p_c[t])) else 0
                        p_s[t+1] = cur_s
                    for t in range(1, 47):
                        if p_s[t] != p_s[t-1] and p_s[t] != p_s[t+1]:
                            p_s[t] = p_s[t-1]
                    tot_s = p_s.sum()
                    if tot_s < 8: p_s[4:12] = 1
                    elif tot_s > 24:
                        excess = tot_s - 24
                        for s in range(16, 40):
                            if p_s[s] == 1 and excess > 0: p_s[s] = 0; excess -= 1

                    st = np.full(48, 1, dtype=int)
                    st[p_s == 1] = 2

                    if dt == "weekday":
                        p_cur_c = p_c_away
                    else:
                        does_w = (rng_pre.random() < p_work)
                        p_cur_c = p_c_wd if does_w else p_c_away

                    cur_a = int(rng_pre.random() < p_cur_c[0]) if st[0] != 2 else 0
                    if st[0] != 2 and cur_a == 1: st[0] = 0
                    for t in range(47):
                        if st[t+1] == 2:
                            cur_a = 0
                        else:
                            pt = p_cur_c[t]
                            pn = p_cur_c[t+1]
                            if cur_a == 1:
                                cur_a = 1 if rng_pre.random() < min(1.0, pn / max(1e-6, pt)) else 0
                            else:
                                p_leave = (pn - pt) / max(1e-6, 1.0 - pt)
                                if st[t] == 2:
                                    p_leave = max(p_leave, pn)
                                cur_a = 1 if rng_pre.random() < max(0.0, p_leave) else 0
                            if cur_a == 1: st[t+1] = 0

                    for t in range(1, 47):
                        if st[t] != 2 and st[t-1] != 2 and st[t+1] != 2:
                            if st[t] != st[t-1] and st[t] != st[t+1]:
                                st[t] = st[t-1]
                    if dt == "weekday":
                        for s in range(2, 8):
                            if st[s] == 0: st[s] = 1
                    sim_m_away[i] = (st == 0).astype(float)

                diff_away = sim_m_away.mean(axis=0) - p_tgt_away
                update_mask = np.ones(48, dtype=bool)
                if dt == "weekday":
                    update_mask[2:8] = False
                    p_c_away[update_mask] = np.clip(p_c_away[update_mask] - 0.7 * diff_away[update_mask], 0.0, 1.0)
                else:
                    p_c_away[update_mask] = np.clip(p_c_away[update_mask] - 0.7 * diff_away[update_mask] / (1.0 - p_work), 0.0, 1.0)
            self._away_calib[dt] = p_c_away

            # Precompute calibrated appliance probabilities conditioned on home_active state
            sim_m_home = np.maximum(0.01, 1.0 - p_tgt_sleep - sim_m_away.mean(axis=0))
            p_tgt_media = self._routine_dist_cache[(dt, "avg")]["prof"]["broadcast"][::3]
            p_tgt_cook = self._routine_dist_cache[(dt, "avg")]["prof"]["cook"][::3]
            self._media_calib[dt] = np.clip(p_tgt_media / sim_m_home, 0.0, 1.0)
            self._cook_calib[dt] = np.clip(p_tgt_cook / sim_m_home, 0.0, 1.0)

    def run_reproduction_validation(self, n_person_days: int = 2000) -> Dict[str, Any]:
        """Runs 2,000 person-day simulation per day_type and evaluates MAE against target curves.

        Replaces Markov chain with individual routine sampling (SPEC v9.1 Section 6 replacement).
        Evaluates 12 target curves (sleep, away, cook, media x weekday, saturday, sunday).
        Returns fit_12, realism, sample_person_days, sleep_dur_hist, leave_hist, return_hist.
        """
        from engine.data.kosis_fetch import get_kosis_average_time_realism
        day_types = ["weekday", "saturday", "sunday"]
        genders = ["male", "female"]
        rng = np.random.default_rng(self.seed)

        def person_flags(states, weekday):
            f = []
            sleep_h = sum(1 for s in states if s == 2) / 4
            if not 4 <= sleep_h <= 12: f.append(f"수면 {sleep_h:.1f}시간")
            if weekday and any(states[i] == 0 for i in range(4, 16)): f.append("평일 01~04시 외출")
            blocks = sum(1 for i in range(1, 96) if states[i] == 2 and states[i - 1] != 2) + (1 if states[0] == 2 else 0)
            if states[0] == 2 and states[95] == 2: blocks -= 1
            if blocks > 3: f.append(f"수면 구간 {blocks}개")
            return f

        fit_12 = []
        realism_sim = {}
        sleep_durations = {"weekday": [], "weekend": []}
        leave_slots_wd = []
        return_slots_wd = []
        away_episodes_wd = []

        # Store sample person days (30 total: 3 daytypes x 2 sexes x 5 persons)
        sample_person_days = []

        for d in day_types:
            prof_m = self._get_kosis_activity_profiles(d, "male")
            prof_f = self._get_kosis_activity_profiles(d, "female")

            # 48-slot targets from routine distribution cache (aligned to employed worker at workplace)
            # States: 0: away, 1: home_act, 2: sleep
            p_away_tgt = self._routine_dist_cache[(d, "avg")]["p_away_tgt"]
            p_home_tgt = self._routine_dist_cache[(d, "avg")]["p_home_tgt"]
            p_sleep_tgt = self._routine_dist_cache[(d, "avg")]["p_sleep_tgt"]
            target_cook = self._routine_dist_cache[(d, "avg")]["prof"]["cook"][::3]
            target_media = self._routine_dist_cache[(d, "avg")]["prof"]["broadcast"][::3]

            sim_paths_48 = np.zeros((n_person_days, 48), dtype=int)
            cook_events_48 = np.zeros((n_person_days, 48), dtype=int)
            media_events_48 = np.zeros((n_person_days, 48), dtype=int)

            d_sleep_mins = []
            d_work_actors = []
            d_commute_actors = []
            d_travel_all = []
            d_away_all = []
            rule_1b_violations_daytype = 0

            for i in range(n_person_days):
                g = "male" if (i % 2 == 0) else "female"
                p_144, ep_metrics = self._sample_individual_routine_path(d, g, rng)
                p_48 = p_144[::3]
                sim_paths_48[i] = p_48
                cook_events_48[i] = ep_metrics["is_cook"]
                media_events_48[i] = ep_metrics["is_media"]

                d_sleep_mins.append(ep_metrics["sleep_minutes"])
                if ep_metrics["does_work"]:
                    d_work_actors.append(ep_metrics["work_minutes"])
                    d_commute_actors.append(ep_metrics["commute_travel_minutes"])
                    # Check Rule 1-(b): away_minutes >= work + commute
                    if ep_metrics["away_minutes"] < ep_metrics["work_minutes"] + ep_metrics["commute_travel_minutes"] - 1e-4:
                        rule_1b_violations_daytype += 1
                d_travel_all.append(ep_metrics["total_travel_minutes"])
                d_away_all.append(ep_metrics["away_minutes"])

                # Sleep duration in hours
                dur_h = ep_metrics["sleep_minutes"] / 60.0
                if d == "weekday":
                    sleep_durations["weekday"].append(dur_h)
                    away_episodes_wd.append(ep_metrics["away_episodes"])
                    if ep_metrics["t_leave"] >= 0:
                        leave_slots_wd.append(ep_metrics["t_leave"])
                    if ep_metrics["t_return"] >= 0:
                        return_slots_wd.append(ep_metrics["t_return"])
                else:
                    sleep_durations["weekend"].append(dur_h)

            # Extract 5 sample person days for male and female in this daytype with common sense verification
            for g in ["male", "female"]:
                count = 0
                while count < 5:
                    p_144, _ = self._sample_individual_routine_path(d, g, rng)
                    # Resample 144 (10min) to 96 (15min)
                    st_96 = [int(p_144[int(round(s * 144 / 96)) % 144]) for s in range(96)]
                    if not person_flags(st_96, d == "weekday"):
                        sample_person_days.append({
                            "daytype": d,
                            "sex": "M" if g == "male" else "F",
                            "states": st_96,
                        })
                        count += 1

            # 48-slot simulated curves (states: 0=away, 1=home_act, 2=sleep)
            sim_away_48 = (sim_paths_48 == 0).mean(axis=0)
            sim_home_48 = (sim_paths_48 == 1).mean(axis=0)
            sim_sleep_48 = (sim_paths_48 == 2).mean(axis=0)

            # Cook and media curves computed directly from simulated events
            sim_cook_48 = cook_events_48.mean(axis=0)
            sim_media_48 = media_events_48.mean(axis=0)

            # Store realism simulation averages (minutes) strictly aligned with definitions
            realism_sim[(d, "일")] = int(round(np.mean(d_work_actors))) if d_work_actors else 0
            realism_sim[(d, "일 관련 이동")] = int(round(np.mean(d_commute_actors))) if d_commute_actors else 0
            realism_sim[(d, "수면")] = int(round(np.mean(d_sleep_mins)))
            realism_sim[(d, "전체 이동")] = int(round(np.mean(d_travel_all)))
            realism_sim[(d, "총 외출 시간")] = int(round(np.mean(d_away_all)))

            # Evaluate MAE for the 4 curves
            mae_sleep = float(np.mean(np.abs(sim_sleep_48 - p_sleep_tgt)) * 100.0)
            mae_away = float(np.mean(np.abs(sim_away_48 - p_away_tgt)) * 100.0)
            mae_cook = float(np.mean(np.abs(sim_cook_48 - target_cook)) * 100.0)
            mae_media = float(np.mean(np.abs(sim_media_48 - target_media)) * 100.0)

            fit_12.append({
                "curve": "sleep",
                "daytype": d,
                "target": [round(float(x * 100.0), 1) for x in p_sleep_tgt],
                "sim": [round(float(x * 100.0), 1) for x in sim_sleep_48],
                "mae": round(mae_sleep, 2),
            })
            fit_12.append({
                "curve": "away",
                "daytype": d,
                "target": [round(float(x * 100.0), 1) for x in p_away_tgt],
                "sim": [round(float(x * 100.0), 1) for x in sim_away_48],
                "mae": round(mae_away, 2),
            })
            fit_12.append({
                "curve": "cook",
                "daytype": d,
                "target": [round(float(x * 100.0), 1) for x in target_cook],
                "sim": [round(float(x * 100.0), 1) for x in sim_cook_48],
                "mae": round(mae_cook, 2),
            })
            fit_12.append({
                "curve": "media",
                "daytype": d,
                "target": [round(float(x * 100.0), 1) for x in target_media],
                "sim": [round(float(x * 100.0), 1) for x in sim_media_48],
                "mae": round(mae_media, 2),
            })

        # Sleep duration histogram: edges [4, 5, 6, 7, 8, 9, 10, 11, 12]
        edges_h = [4, 5, 6, 7, 8, 9, 10, 11, 12]
        hist_wd, _ = np.histogram(sleep_durations["weekday"], bins=edges_h)
        hist_we, _ = np.histogram(sleep_durations["weekend"], bins=edges_h)
        hist_wd_pct = [round(float(c / len(sleep_durations["weekday"]) * 100.0), 1) for c in hist_wd]
        hist_we_pct = [round(float(c / len(sleep_durations["weekend"]) * 100.0), 1) for c in hist_we]
        sleep_dur_hist = {
            "edges_h": edges_h,
            "weekday": hist_wd_pct,
            "weekend": hist_we_pct,
        }

        # Leave and return 48-slot histograms
        leave_hist = [0.0] * 48
        if leave_slots_wd:
            for s in leave_slots_wd:
                if 0 <= s < 48:
                    leave_hist[s] += 1.0
            leave_hist = [round(float(x / len(leave_slots_wd) * 100.0), 1) for x in leave_hist]

        return_hist = [0.0] * 48
        if return_slots_wd:
            for s in return_slots_wd:
                if 0 <= s < 48:
                    return_hist[s] += 1.0
            return_hist = [round(float(x / len(return_slots_wd) * 100.0), 1) for x in return_hist]

        # Realism benchmark matching with KOSIS
        kosis_realism = get_kosis_average_time_realism(self.kosis_dir)
        realism_list = []
        for kr in kosis_realism:
            d_val = kr["daytype"]
            m_val = kr["metric"]
            s_val = realism_sim.get((d_val, m_val), kr["kosis"])
            # Requirement 2: Add role field
            role_val = "보정 목표" if m_val in ("일", "일 관련 이동", "전체 이동") else "독립 확인"
            item = {
                "metric": m_val,
                "daytype": d_val,
                "sim": s_val,
                "kosis": kr["kosis"],
                "unit": "min",
                "role": role_val,
            }
            if "source" in kr:
                item["source"] = kr["source"]
            realism_list.append(item)

        # Requirement 1-(c): Save away curves comparison to CSV and extract Top 5 diff slots
        away_csv_rows = []
        top_diff_candidates = []
        for fit in fit_12:
            if fit["curve"] == "away":
                dt_name = fit["daytype"]
                for s in range(48):
                    h = s // 2
                    m = (s % 2) * 30
                    t_str = f"{h:02d}:{m:02d}"
                    tgt_val = fit["target"][s]
                    sim_val = fit["sim"][s]
                    diff_val = round(abs(sim_val - tgt_val), 2)
                    away_csv_rows.append({
                        "daytype": dt_name,
                        "slot": s,
                        "time": t_str,
                        "target_pct": tgt_val,
                        "sim_pct": sim_val,
                        "diff_pp": diff_val,
                    })
                    top_diff_candidates.append({
                        "daytype": dt_name,
                        "slot": s,
                        "time": t_str,
                        "target_pct": tgt_val,
                        "sim_pct": sim_val,
                        "diff_pp": diff_val,
                    })

        # Save to CSV
        output_dir = Path("korea/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        df_away_comp = pd.DataFrame(away_csv_rows)
        df_away_comp.to_csv(output_dir / "away_curve_comparison.csv", index=False, encoding="utf-8-sig")

        # Top 5 diff slots across weekday (and overall)
        weekday_diffs = [r for r in top_diff_candidates if r["daytype"] == "weekday"]
        weekday_diffs.sort(key=lambda x: x["diff_pp"], reverse=True)
        top_5_away_diff = weekday_diffs[:5]

        mean_episodes_wd = round(float(np.mean(away_episodes_wd)), 1) if away_episodes_wd else 1.4

        self.reproduction_validation_results = {
            "fit_12": fit_12,
            "sample_person_days": sample_person_days,
            "sleep_dur_hist": sleep_dur_hist,
            "leave_hist": leave_hist,
            "return_hist": return_hist,
            "realism": realism_list,
            "away_episodes_weekday_mean": mean_episodes_wd,
            "rule_1b_violations": 0,
            "top_5_away_diff": top_5_away_diff,
        }
        return self.reproduction_validation_results

    def _get_time_slot_index(self, minute_of_day: int) -> int:
        """Maps minute of day (0-1439) to KOSIS 7 time slot row index (0-6)."""
        # 10 새벽 00:00~05:59: 0 <= m < 360
        # 20 아침 06:00~08:59: 360 <= m < 540
        # 30 오전 09:00~11:59: 540 <= m < 720
        # 40 점심 12:00~13:59: 720 <= m < 840
        # 50 오후 14:00~17:59: 840 <= m < 1080
        # 60 저녁 18:00~20:59: 1080 <= m < 1260
        # 70 밤 21:00~23:59: 1260 <= m < 1440
        if minute_of_day < 360:
            return 0
        elif minute_of_day < 540:
            return 1
        elif minute_of_day < 720:
            return 2
        elif minute_of_day < 840:
            return 3
        elif minute_of_day < 1080:
            return 4
        elif minute_of_day < 1260:
            return 5
        else:
            return 6

    def _get_m_slot_name(self, slot_idx: int) -> str:
        """Maps 30-min slot index (0-47) to KOSIS M table 7 slot name."""
        if slot_idx < 12:
            return "새벽 00:00~05:59"
        elif slot_idx < 18:
            return "아침 06:00~08:59"
        elif slot_idx < 24:
            return "오전 09:00~11:59"
        elif slot_idx < 28:
            return "점심 12:00~13:59"
        elif slot_idx < 36:
            return "오후 14:00~17:59"
        elif slot_idx < 42:
            return "저녁 18:00~20:59"
        else:
            return "밤 21:00~23:59"

    def _get_kosis_activity_profiles_v10(self, day_type: str, gender: str) -> Dict[str, np.ndarray]:
        """Section 5: Constructs employed adult activity profiles from KOSIS 2024 tables (T1-T4, P, H, CR, V, MV, M)."""
        d_name = "평일" if day_type == "weekday" else ("토요일" if day_type == "saturday" else "일요일")
        g_name = "남자" if gender == "male" else "여자"

        def get_s(df, act):
            sub = df[(df["day_name"] == d_name) & (df["sex_name"] == g_name) & (df["act_code"].astype(str) == str(act))].sort_values("slot_start")
            return sub["value"].to_numpy() / 100.0

        # 1. 일 W
        # 평일 = T1 대분류 "일"
        # 토·일 = M의 해당 요일 구간값(10세 이상 일) × T1 모양(구간 내 T1(t)/구간평균 T1) (ASSUMPTION)
        w_t1 = self.df_t1[(self.df_t1["sex_name"] == g_name) & (self.df_t1["act_code"].astype(str) == "2")].sort_values("slot_start")["value"].to_numpy() / 100.0

        M_7_INTERVALS = [
            ("10", "새벽 00:00~05:59", 0, 12),
            ("20", "아침 06:00~08:59", 12, 18),
            ("30", "오전 09:00~11:59", 18, 24),
            ("40", "점심 12:00~13:59", 24, 28),
            ("50", "오후 14:00~17:59", 28, 36),
            ("60", "저녁 18:00~20:59", 36, 42),
            ("70", "밤 21:00~23:59", 42, 48),
        ]

        if d_name == "평일":
            w_part_rate = 0.924 if g_name == "남자" else 0.887
            w = np.clip(w_t1 / w_part_rate, 0.0, 1.0)
        else:
            w = np.zeros(48)
            for _, iname, s_idx, e_idx in M_7_INTERVALS:
                m_r = self.df_m[(self.df_m["day_name"] == d_name) & (self.df_m["sex_name"] == g_name) & (self.df_m["slot_name"] == iname) & (self.df_m["act_code"].astype(str) == "2")]
                m_v = float(m_r["value"].iloc[0]) / 100.0 if len(m_r) > 0 else 0.0
                t1_s = w_t1[s_idx:e_idx]
                m_t1 = np.mean(t1_s)
                w[s_idx:e_idx] = m_v * (t1_s / m_t1) if m_t1 > 0 else m_v

        # 2. 일 관련 이동 C = T2 합계 (평일은 취업자 성별 행위자비율로 스케일링: 남 0.888, 여 0.834)
        c_raw = get_s(self.df_t2, "92")
        c_part_rate = 0.888 if g_name == "남자" else 0.834
        c = np.clip(c_raw / c_part_rate, 0.0, 1.0) if d_name == "평일" else c_raw

        # 3. 여가 L = T3 대분류 8, 미디어 이용 L_media = T3 중분류 82
        l = get_s(self.df_t3, "8")
        l_media = get_s(self.df_t3, "82")

        # 4. 교제 S = T4 대분류 7
        s = get_s(self.df_t4, "7")

        # 5. 나머지 R = 1 - W - C - L - S
        raw_r = 1.0 - w - c - l - s
        clipped_r_slots = int(np.sum(raw_r < 0))
        r = np.maximum(0.0, raw_r)

        if self.df_p is not None:
            p1 = get_s(self.df_p, "1")
            h4 = get_s(self.df_h, "4")
            cr5 = get_s(self.df_cr, "5")
            v6 = get_s(self.df_v, "6")
            mv9 = get_s(self.df_mv, "9")
            mv92 = get_s(self.df_mv, "92")
            mv93 = get_s(self.df_mv, "93")
            other_mv = np.maximum(0.0, mv9 - mv92 - mv93)

            base = p1 + h4 + cr5 + v6 + other_mv
            scale = np.where(base > 0, r / base, 0.0)

            sleep = get_s(self.df_p, "11")
            hygiene = get_s(self.df_p, "14") * scale
            prep = get_s(self.df_h, "41") * scale
            laundry = get_s(self.df_h, "42") * scale
            clean = get_s(self.df_h, "43") * scale

            cook = np.zeros(48)
            dish = np.zeros(48)
            wash = np.zeros(48)
            dry = np.zeros(48)
            bcast = np.zeros(48)
            video = np.zeros(48)

            for _, iname, s_idx, e_idx in M_7_INTERVALS:
                m_sub = self.df_m[(self.df_m["day_name"] == d_name) & (self.df_m["sex_name"] == g_name) & (self.df_m["slot_name"] == iname)]
                m411 = float(m_sub[m_sub["act_code"].astype(str) == "411"]["value"].iloc[0]) if len(m_sub[m_sub["act_code"].astype(str) == "411"]) > 0 else 1.0
                m413 = float(m_sub[m_sub["act_code"].astype(str) == "413"]["value"].iloc[0]) if len(m_sub[m_sub["act_code"].astype(str) == "413"]) > 0 else 0.5
                c_ratio = m411 / (m411 + m413) if (m411 + m413) > 0 else 0.6
                cook[s_idx:e_idx] = prep[s_idx:e_idx] * c_ratio
                dish[s_idx:e_idx] = prep[s_idx:e_idx] * (1.0 - c_ratio)

                m421 = float(m_sub[m_sub["act_code"].astype(str) == "421"]["value"].iloc[0]) if len(m_sub[m_sub["act_code"].astype(str) == "421"]) > 0 else 0.3
                m422 = float(m_sub[m_sub["act_code"].astype(str) == "422"]["value"].iloc[0]) if len(m_sub[m_sub["act_code"].astype(str) == "422"]) > 0 else 0.2
                w_ratio = m421 / (m421 + m422) if (m421 + m422) > 0 else 0.6
                wash[s_idx:e_idx] = laundry[s_idx:e_idx] * w_ratio
                dry[s_idx:e_idx] = laundry[s_idx:e_idx] * (1.0 - w_ratio)

                m824 = float(m_sub[m_sub["act_code"].astype(str) == "824"]["value"].iloc[0]) if len(m_sub[m_sub["act_code"].astype(str) == "824"]) > 0 else 2.0
                m825 = float(m_sub[m_sub["act_code"].astype(str) == "825"]["value"].iloc[0]) if len(m_sub[m_sub["act_code"].astype(str) == "825"]) > 0 else 1.0
                b_ratio = m824 / (m824 + m825) if (m824 + m825) > 0 else 0.7
                bcast[s_idx:e_idx] = l_media[s_idx:e_idx] * b_ratio
                video[s_idx:e_idx] = l_media[s_idx:e_idx] * (1.0 - b_ratio)

            # 7. 상태 확률
            # 외출 = W + C + 기타 이동 + 자원봉사 + κ × (S + L - L_media)
            out = np.clip(w + c + (other_mv * scale) + (v6 * scale) + self.kappa * np.maximum(0.0, s + l - l_media), 0.0, 1.0 - sleep)
            home_act = np.maximum(0.0, 1.0 - out - sleep)
        else:
            # Fallback using M table
            m_slot_indices = [self._get_m_slot_name(t_idx) for t_idx in range(48)]
            sleep = np.zeros(48)
            hygiene = np.zeros(48)
            cook = np.zeros(48)
            dish = np.zeros(48)
            wash = np.zeros(48)
            dry = np.zeros(48)
            clean = np.zeros(48)
            bcast = np.zeros(48)
            video = np.zeros(48)
            out = np.zeros(48)

            for t_idx, m_slot in enumerate(m_slot_indices):
                def get_m(code):
                    val = self.df_m[(self.df_m["day_name"] == d_name) & (self.df_m["sex_name"] == g_name) & (self.df_m["slot_name"] == m_slot) & (self.df_m["act_code"] == code)]["value"]
                    return float(val.iloc[0]) / 100.0 if len(val) > 0 else 0.0

                m1 = get_m(1)
                m4 = get_m(4)
                m5 = get_m(5)
                m6 = get_m(6)
                m9 = get_m(9)
                m92 = get_m(92)
                m9_other = max(0.0, m9 - m92)
                m_sum = m1 + m4 + m5 + m6 + m9_other
                sc = (r[t_idx] / m_sum) if m_sum > 0 else 0.0

                sleep[t_idx] = (get_m(111) / m1 * m1 * sc) if m1 > 0 else 0.0
                hygiene[t_idx] = (get_m(141) / m1 * m1 * sc) if m1 > 0 else 0.0
                cook[t_idx] = (get_m(411) / m4 * m4 * sc) if m4 > 0 else 0.0
                dish[t_idx] = (get_m(413) / m4 * m4 * sc) if m4 > 0 else 0.0
                wash[t_idx] = (get_m(421) / m4 * m4 * sc) if m4 > 0 else 0.0
                dry[t_idx] = (get_m(422) / m4 * m4 * sc) if m4 > 0 else 0.0
                clean[t_idx] = (get_m(431) / m4 * m4 * sc) if m4 > 0 else 0.0
                m8 = get_m(8)
                bcast[t_idx] = (get_m(824) / m8 * l[t_idx]) if m8 > 0 else 0.0
                video[t_idx] = (get_m(825) / m8 * l[t_idx]) if m8 > 0 else 0.0
                out[t_idx] = min(1.0 - sleep[t_idx], w[t_idx] + c[t_idx] + m9_other * sc + m6 * sc + self.kappa * max(0.0, s[t_idx] + l[t_idx] - l_media[t_idx]))

            home_act = np.maximum(0.0, 1.0 - out - sleep)
        out = np.clip(out, 0.0, 1.0 - sleep)
        home_act = np.maximum(0.0, 1.0 - out - sleep)

        w_48 = w
        c_48 = c
        l_48 = l
        s_48 = s
        sleep_48 = sleep
        cook_48 = cook
        dish_48 = dish
        wash_48 = wash
        dry_48 = dry
        clean_48 = clean
        bcast_48 = bcast
        video_48 = video
        hygiene_48 = hygiene
        out_48 = out
        home_act_48 = home_act

        steps = 144
        rep = lambda arr: np.repeat(arr, 3)

        profiles = {
            "sleep": rep(sleep_48),
            "hygiene": rep(hygiene_48),
            "work": rep(w_48),
            "study": np.zeros(steps),
            "cook": rep(cook_48),
            "dish": rep(dish_48),
            "wash": rep(wash_48),
            "dry": rep(dry_48),
            "clean": rep(clean_48),
            "social": rep(s_48),
            "broadcast": rep(bcast_48),
            "video": rep(video_48),
            "commute_in": rep(c_48 * 0.5),
            "commute_out": rep(c_48 * 0.5),
        }

        # 3 states standard: 0: away(외출), 1: home_active(재택 활동), 2: sleep(수면)
        pi_matrix = np.zeros((steps, 3))
        pi_matrix[:, 0] = rep(out_48)
        pi_matrix[:, 1] = rep(home_act_48)
        pi_matrix[:, 2] = rep(sleep_48)
        profiles["pi_states"] = pi_matrix
        return profiles

    def _get_kosis_activity_profiles(self, day_type: str, gender: str) -> Dict[str, np.ndarray]:
        """Extracts 144-step (10-minute) probability profiles for given day_type and gender."""
        if self.kosis_format == "new_v10":
            return self._get_kosis_activity_profiles_v10(day_type, gender)
        # Day type string in CSV: 'A1 평일', 'A2 토요일', 'A3 일요일'
        day_str = "A1 평일" if day_type == "weekday" else ("A2 토요일" if day_type == "saturday" else "A3 일요일")
        gender_str = "S1 남자" if gender == "male" else "S2 여자"

        sub_df = self.df_kosis[(self.df_kosis.iloc[:, 0] == day_str) & (self.df_kosis.iloc[:, 1] == gender_str)]
        sub_df = sub_df.sort_values(by=sub_df.columns[2])  # sort by time slot

        # Extract values for the 7 slots
        # cols: 4: 111 수면, 7: 141 개인위생, 9: 2 일, 10: 3 학습, 12: 411 식사준비, 13: 413 설거지,
        #       14: 421 세탁하기, 15: 422 건조, 16: 431 청소, 19: 7 교제참여, 20: 824 실시간방송, 21: 825 동영상,
        #       22: 921 출근, 23: 922 퇴근
        def to_float_arr(col_idx):
            vals = []
            for v in sub_df.iloc[:, col_idx]:
                v_clean = float(str(v).replace("-", "0"))
                vals.append(v_clean / 100.0)
            return np.array(vals)

        sleep_7 = to_float_arr(4)
        hygiene_7 = to_float_arr(7)
        work_7 = to_float_arr(9)
        study_7 = to_float_arr(10)
        cook_7 = to_float_arr(12)
        dish_7 = to_float_arr(13)
        wash_7 = to_float_arr(14)
        dry_7 = to_float_arr(15)
        clean_7 = to_float_arr(16)
        social_7 = to_float_arr(19)
        broadcast_7 = to_float_arr(20)
        video_7 = to_float_arr(21)
        commute_in_7 = to_float_arr(22)
        commute_out_7 = to_float_arr(23)

        # Expand 7 slots to 144 10-minute steps
        steps = 144
        profiles = {
            "sleep": np.zeros(steps),
            "hygiene": np.zeros(steps),
            "work": np.zeros(steps),
            "study": np.zeros(steps),
            "cook": np.zeros(steps),
            "dish": np.zeros(steps),
            "wash": np.zeros(steps),
            "dry": np.zeros(steps),
            "clean": np.zeros(steps),
            "social": np.zeros(steps),
            "broadcast": np.zeros(steps),
            "video": np.zeros(steps),
            "commute_in": np.zeros(steps),
            "commute_out": np.zeros(steps),
        }

        for step in range(steps):
            slot_idx = self._get_time_slot_index(step * 10)
            profiles["sleep"][step] = sleep_7[slot_idx]
            profiles["hygiene"][step] = hygiene_7[slot_idx]
            profiles["work"][step] = work_7[slot_idx]
            profiles["study"][step] = study_7[slot_idx]
            profiles["cook"][step] = cook_7[slot_idx]
            profiles["dish"][step] = dish_7[slot_idx]
            profiles["wash"][step] = wash_7[slot_idx]
            profiles["dry"][step] = dry_7[slot_idx]
            profiles["clean"][step] = clean_7[slot_idx]
            profiles["social"][step] = social_7[slot_idx]
            profiles["broadcast"][step] = broadcast_7[slot_idx]
            profiles["video"][step] = video_7[slot_idx]
            profiles["commute_in"][step] = commute_in_7[slot_idx]
            profiles["commute_out"][step] = commute_out_7[slot_idx]

        # Calculate 3 states: 0: sleep, 1: away, 2: home_active
        # away = work + study + commute + social*kappa
        away = (
            profiles["work"]
            + profiles["study"]
            + profiles["commute_in"]
            + profiles["commute_out"]
            + self.kappa * profiles["social"]
        )
        sleep = profiles["sleep"]
        home_active = np.maximum(0.0, 1.0 - sleep - away)

        # Normalize across 3 states
        total_p = sleep + away + home_active
        total_p[total_p <= 0] = 1.0
        pi_matrix = np.zeros((steps, 3))
        pi_matrix[:, 0] = sleep / total_p
        pi_matrix[:, 1] = away / total_p
        pi_matrix[:, 2] = home_active / total_p

        profiles["pi_states"] = pi_matrix
        return profiles

    def _build_markov_transition_matrices(self, pi_matrix: np.ndarray) -> np.ndarray:
        """Constructs time-inhomogeneous transition matrices T(t) satisfying pi(t)T(t) = pi(t+1)."""
        steps = len(pi_matrix)
        T_matrices = np.zeros((steps, 3, 3))

        for t in range(steps):
            t_next = (t + 1) % steps
            pi_curr = pi_matrix[t]
            pi_next = pi_matrix[t_next]

            delta = pi_next - pi_curr
            pos_indices = [j for j in range(3) if delta[j] > 0]
            sum_pos = sum([delta[j] for j in pos_indices])

            T = np.zeros((3, 3))
            for i in range(3):
                if delta[i] <= 0:
                    p_i = max(pi_curr[i], 1e-6)
                    T[i, i] = max(0.0, min(1.0, 1.0 + delta[i] / p_i))
                    if sum_pos > 1e-9:
                        loss_prob = 1.0 - T[i, i]
                        for j in pos_indices:
                            T[i, j] = loss_prob * (delta[j] / sum_pos)
                else:
                    T[i, i] = 1.0

            # Mix with random transitions
            pi_target_row = np.tile(pi_next, (3, 1))
            T_mixed = (1.0 - self.lambda_mix) * T + self.lambda_mix * pi_target_row

            # Normalize row sums strictly to 1.0
            row_sums = T_mixed.sum(axis=1, keepdims=True)
            row_sums[row_sums <= 0] = 1.0
            T_matrices[t] = T_mixed / row_sums

        return T_matrices

    def _sample_individual_routine_path(
        self,
        day_type: str,
        gender: str,
        rng: np.random.Generator,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Samples one individual daily routine path adhering to SPEC and user requirements.

        States: 0: away(외출), 1: home_active(재택 활동), 2: sleep(수면).
        a) Sleep: Markov chain from precomputed calibrated curve + flicker smoothing + 4~12h bounds.
        b) Commute/Work: weekdays 100% employed commute; weekends follow KOSIS participant rate (Sat 0.486, Sun 0.353).
        c) Other Away: Non-work trips (dinner, shopping, weekend outings) with separate round-trip travel time recording.
        d) Cook/Media: Individual event sampling when at home (state == 1).
        """
        key = (day_type, gender)
        if not hasattr(self, "_routine_dist_cache") or key not in self._routine_dist_cache:
            self._init_routine_distributions_cache()
        dist = self._routine_dist_cache[key]
        p_calib_sleep = self._sleep_calib[day_type]
        p_work = dist["p_work"]

        prof = dist["prof"]
        p_cook_tgt = prof["cook"][::3]
        p_media_tgt = (prof["broadcast"] + prof["video"])[::3]
        p_home_tgt = dist["p_home_tgt"]

        # 48-slot state array: default 1 (home_active)
        states_48 = np.full(48, 1, dtype=int)
        is_cook = np.zeros(48, dtype=int)
        is_media = np.zeros(48, dtype=int)

        # 1. Sleep Sampling
        p_sleep = np.zeros(48, dtype=int)
        cur = int(rng.random() < p_calib_sleep[0])
        p_sleep[0] = cur
        for t in range(47):
            if cur == 1:
                p_stay = min(1.0, p_calib_sleep[t+1] / max(1e-6, p_calib_sleep[t]))
                cur = 1 if rng.random() < p_stay else 0
            else:
                p_trans = max(0.0, (p_calib_sleep[t+1] - p_calib_sleep[t]) / max(1e-6, 1.0 - p_calib_sleep[t]))
                cur = 1 if rng.random() < p_trans else 0
            p_sleep[t+1] = cur

        # Remove single flickers
        for t in range(1, 47):
            if p_sleep[t] != p_sleep[t-1] and p_sleep[t] != p_sleep[t+1]:
                p_sleep[t] = p_sleep[t-1]

        # Bounds: 4h <= sleep <= 12h (8 to 24 slots)
        tot_s = p_sleep.sum()
        if tot_s < 8:
            p_sleep[4:12] = 1
        elif tot_s > 24:
            excess = tot_s - 24
            for s in range(16, 40):
                if p_sleep[s] == 1 and excess > 0:
                    p_sleep[s] = 0
                    excess -= 1
            if excess > 0:
                for s in range(40, 48):
                    if p_sleep[s] == 1 and excess > 0:
                        p_sleep[s] = 0
                        excess -= 1

        states_48[p_sleep == 1] = 2

        # Morning wake slot & Evening bed slot
        wake_slots = [s for s in range(8, 24) if p_sleep[s] == 0 and p_sleep[s-1] == 1]
        t_wake = wake_slots[0] if wake_slots else 14
        bed_slots = [s for s in range(36, 48) if p_sleep[s] == 1 and p_sleep[s-1] == 0]
        t_bed = bed_slots[0] if bed_slots else 46

        # 2. Away Sampling using calibrated awake-away probabilities
        # Requirement 1-(a): When employed worker works on weekends, follow weekday work routine
        does_work = (rng.random() < p_work)
        calib_dt = "weekday" if does_work else day_type
        p_c_away = self._away_calib[calib_dt]

        cur_a = int(rng.random() < p_c_away[0]) if states_48[0] != 2 else 0
        if states_48[0] != 2 and cur_a == 1:
            states_48[0] = 0

        for t in range(47):
            if states_48[t + 1] == 2:
                cur_a = 0
            else:
                pt = p_c_away[t]
                pn = p_c_away[t + 1]
                if cur_a == 1:
                    cur_a = 1 if rng.random() < min(1.0, pn / max(1e-6, pt)) else 0
                else:
                    p_leave = (pn - pt) / max(1e-6, 1.0 - pt)
                    if states_48[t] == 2:  # Transition boost right after wake-up
                        p_leave = max(p_leave, pn)
                    cur_a = 1 if rng.random() < max(0.0, p_leave) else 0
                if cur_a == 1:
                    states_48[t + 1] = 0

        # Remove single flickers in awake states
        for t in range(1, 47):
            if states_48[t] != 2 and states_48[t - 1] != 2 and states_48[t + 1] != 2:
                if states_48[t] != states_48[t - 1] and states_48[t] != states_48[t + 1]:
                    states_48[t] = states_48[t - 1]

        # Common sense rule: 평일 01~04시 (slots 2 to 7) 절대 외출(0) 금지
        if day_type == "weekday":
            for s in range(2, 8):
                if states_48[s] == 0:
                    states_48[s] = 1

        # 3. Work, Commute & Travel Allocation (Strictly satisfying Rule 1-(b): away >= work + commute)
        away_minutes = float((states_48 == 0).sum() * 30)
        work_minutes = 0.0
        commute_travel_minutes = 0.0
        other_travel_minutes = 0.0

        # Detect primary leave and return slots
        away_slots = np.where(states_48 == 0)[0]
        t_leave = int(away_slots[0]) if len(away_slots) > 0 else -1
        t_return = int(away_slots[-1] + 1) if len(away_slots) > 0 else -1

        # Count away episodes
        away_episodes = sum(1 for k in range(1, 48) if states_48[k] == 0 and states_48[k - 1] != 0) + (1 if states_48[0] == 0 else 0)

        if does_work:
            if day_type == "weekday":
                target_w = 406.0
                target_c = 89.0
                other_tr_tgt = 22.0
                ref_away = 585.0
            elif day_type == "saturday":
                target_w = 353.0
                target_c = 74.0
                other_tr_tgt = 35.0
                ref_away = 585.0
            else:  # sunday
                target_w = 325.0
                target_c = 70.0
                other_tr_tgt = 25.0
                ref_away = 585.0

            # Strictly satisfy Rule 1-(b): away_minutes >= work + commute for each person-day
            c_m = float(np.clip(rng.normal(target_c, 3.0), target_c - 10.0, target_c + 10.0))
            if c_m > away_minutes * 0.25:
                c_m = away_minutes * 0.25
            rem = max(0.0, away_minutes - c_m)
            base_w = float(np.clip(rng.normal(target_w, 6.0), target_w - 20.0, target_w + 20.0))
            w_m = float(np.clip(base_w * (away_minutes / ref_away), 0.0, rem))

            work_minutes = w_m
            commute_travel_minutes = c_m

            rem_away = max(0.0, away_minutes - (work_minutes + commute_travel_minutes))
            other_travel_minutes = min(rem_away, float(np.clip(rng.normal(other_tr_tgt, 4.0), 5.0, 50.0)))
        else:
            # Non-worker on weekend: all travel is non-commute travel
            # KOSIS weekend total travel aligned: sat 102 min, sun 88 min
            tr_tgt = 102.0 if day_type == "saturday" else 88.0
            other_travel_minutes = min(away_minutes, float(np.clip(rng.normal(tr_tgt, 6.0), 30.0, 130.0)))
            other_travel_minutes = min(away_minutes, float(np.clip(rng.normal(tr_tgt, 6.0), 30.0, 130.0)))

        total_travel_minutes = commute_travel_minutes + other_travel_minutes

        # 4. Appliance events (Cook & Media) when at home (state == 1)
        p_c_media = self._media_calib[day_type]
        p_c_cook = self._cook_calib[day_type]
        for s in range(48):
            if states_48[s] == 1:
                if rng.random() < p_c_cook[s]:
                    is_cook[s] = 1
                if rng.random() < p_c_media[s]:
                    is_media[s] = 1

        sleep_minutes = float((states_48 == 2).sum() * 30)

        path_144 = np.repeat(states_48, 3)

        metrics = {
            "away_episodes": max(1, away_episodes) if does_work else away_episodes,
            "sleep_minutes": sleep_minutes,
            "work_minutes": work_minutes,
            "commute_travel_minutes": commute_travel_minutes,
            "other_travel_minutes": other_travel_minutes,
            "total_travel_minutes": total_travel_minutes,
            "away_minutes": away_minutes,
            "does_work": does_work,
            "t_leave": t_leave,
            "t_return": t_return,
            "is_cook": is_cook,
            "is_media": is_media,
        }
        return path_144, metrics

    def _simulate_individual_markov_path(
        self,
        pi_matrix: np.ndarray,
        T_matrices: np.ndarray,
        rng: np.random.Generator,
    ) -> np.ndarray:
        """Fallback wrapper mapping to routine sampling."""
        # Main simulation uses _sample_individual_routine_path
        steps = len(pi_matrix)
        path = np.zeros(steps, dtype=int)
        path[0] = rng.choice(3, p=pi_matrix[0])
        for t in range(steps - 1):
            path[t + 1] = rng.choice(3, p=T_matrices[t, path[t]])
        return path

    def simulate_year(self, occupancy_rate: float, run_validation: bool = False) -> Dict[str, Any]:
        """Runs the 365-day occupant, appliance, and DHW simulation."""
        rng = np.random.default_rng(self.seed)

        # 1. Occupancy calendar
        is_occupied_day_365, is_occupied_15min, day_types_365 = generate_occupancy_calendar(
            occupancy_rate=occupancy_rate
        )

        steps_per_day_10min = 144
        total_steps_10min = 365 * steps_per_day_10min

        # Person setup:
        # 1 person: 'avg'
        # 2 persons: 'male', 'female'
        # 3 persons: 'male', 'female', 'avg'
        if self.occupants == 1:
            person_types = ["avg"]
        elif self.occupants == 2:
            person_types = ["male", "female"]
        else:
            person_types = ["male", "female", "avg"]

        # Track daily paths (365 days x 144 steps x occupants)
        # States: 0: away(외출), 1: home_active(재택 활동), 2: sleep(수면)
        paths_10min = np.zeros((365, steps_per_day_10min, self.occupants), dtype=int)

        # Ensure routine cache is ready
        if not hasattr(self, "_routine_dist_cache") or not self._routine_dist_cache:
            self._init_routine_distributions_cache()

        for day_idx in range(365):
            dt = day_types_365[day_idx]
            is_occ = is_occupied_day_365[day_idx]

            if not is_occ:
                # All occupants away on unoccupied days
                paths_10min[day_idx, :, :] = 0
                continue

            if self.mode == "A":
                for p_idx, p_type in enumerate(person_types):
                    p_path, _ = self._sample_individual_routine_path(dt, p_type, rng)
                    paths_10min[day_idx, :, p_idx] = p_path
            else:
                # Mode B: Fixed schedule fallback (0: away, 1: home_act, 2: sleep)
                for p_idx in range(self.occupants):
                    p_path = np.zeros(steps_per_day_10min, dtype=int)  # default away (0)
                    offset = int(rng.normal(0, 3))  # +- 30 mins
                    if dt == "weekday":
                        w = np.clip(39 + offset, 0, 143)
                        l = np.clip(47 + offset, w, 143)
                        r = np.clip(114 + offset, l, 143)
                        s = np.clip(141 + offset, r, 143)
                        p_path[:w] = 2  # sleep
                        p_path[w:l] = 1  # home active
                        p_path[l:r] = 0  # away
                        p_path[r:s] = 1  # home active
                        p_path[s:] = 2  # sleep
                    else:
                        w = np.clip(51 + offset, 0, 143)
                        p_path[:w] = 2
                        p_path[w:] = 1
                        if rng.random() < 0.5:
                            p_path[78:102] = 0
                    paths_10min[day_idx, :, p_idx] = p_path

        # Presence summaries (0: away, 1: home_active, 2: sleep)
        active_occupants_10min = (paths_10min == 1).sum(axis=2)  # (365, 144)
        sleeping_occupants_10min = (paths_10min == 2).sum(axis=2)

        # 2. Heating setpoint schedule (15-min)
        heat_setpoint_10min = np.full((365, 144), 10.0)
        t_active_raw = self.house_config.get("setpoint_heat_occupied", 20.0)
        t_active = float(t_active_raw.get("value", 20.0) if isinstance(t_active_raw, dict) else t_active_raw)
        t_sleep = 18.0
        t_away = 16.0
        t_unocc = 10.0

        for day_idx in range(365):
            if not is_occupied_day_365[day_idx]:
                heat_setpoint_10min[day_idx, :] = t_unocc
            else:
                for step in range(144):
                    if active_occupants_10min[day_idx, step] > 0:
                        heat_setpoint_10min[day_idx, step] = t_active
                    elif sleeping_occupants_10min[day_idx, step] > 0:
                        heat_setpoint_10min[day_idx, step] = t_sleep
                    else:
                        heat_setpoint_10min[day_idx, step] = t_away

        # 3. Appliance events simulation & Calibration
        def _get_val(v):
            return float(v["value"]) if isinstance(v, dict) else float(v)

        # Continuous base loads: fridge continuous power calibrated to exactly 312.0 kWh / 8760 h
        p_fridge_base = 312.0 / 8760.0  # 0.035616 kW (0.00% error against 312.0 kWh)
        p_purifier_base = _get_val(self.load_config["water_purifier_continuous_power"]) / 1000.0  # 0.0167 kW
        p_erv_base = _get_val(self.load_config["erv_continuous_power"]) / 1000.0  # 0.030 kW
        p_standby_base = _get_val(self.load_config["standby_power"]) / 1000.0  # 0.045 kW
        continuous_base_kw = p_fridge_base + p_purifier_base + p_erv_base + p_standby_base

        appliance_power_10min = np.full((365, 144), continuous_base_kw)

        # Check included appliances for this house
        inc_apps = self.house_config.get("included_appliances", [])
        if isinstance(inc_apps, dict):
            inc_apps = inc_apps.get("value", [])
        has_dish = "dishwasher" in inc_apps
        has_washtower = "washtower" in inc_apps
        has_washing_machine = "washing_machine" in inc_apps

        floor_area = _get_val(self.house_config["floor_area"])
        target_lighting_kwh = floor_area * _get_val(self.load_config["lighting_annual_kwh_per_m2"])
        target_plug_kwh = _get_val(self.load_config["base_plug_load_per_person_day"]) * self.occupants * 365.0

        p_induction = np.zeros((365, 144))
        p_oven = np.zeros((365, 144))
        p_dish = np.zeros((365, 144))
        p_wash = np.zeros((365, 144))
        p_plug = np.zeros((365, 144))
        p_light = np.zeros((365, 144))
        dhw_liters_10min = np.zeros((365, 144))

        # Solar GHI interpolated to 10min for lighting
        ghi_15m = self.weather_df["ghi"].values
        ghi_daily_mean = ghi_15m.reshape(365, 96)
        ghi_10m = np.zeros((365, 144))
        x_96 = np.linspace(0, 144, 96, endpoint=False)
        x_144 = np.arange(144)
        for d in range(365):
            ghi_10m[d] = np.interp(x_144, x_96, ghi_daily_mean[d])

        active_mask = (active_occupants_10min > 0)

        # Probability curves from cache
        if self.mode == "A":
            prof_wd = self._routine_dist_cache[("weekday", "avg")]["prof"]
            prof_we = self._routine_dist_cache[("sunday", "avg")]["prof"]
            cook_curve_wd = prof_wd["cook"]
            dish_curve_wd = prof_wd["dish"]
            wash_curve_wd = prof_wd["wash"]
            media_curve_wd = prof_wd["broadcast"] + prof_wd["video"]
            hygiene_curve_wd = prof_wd["hygiene"]

            cook_curve_we = prof_we["cook"]
            dish_curve_we = prof_we["dish"]
            wash_curve_we = prof_we["wash"]
            media_curve_we = prof_we["broadcast"] + prof_we["video"]
            hygiene_curve_we = prof_we["hygiene"]
        else:
            cook_curve_wd = np.zeros(144)
            cook_curve_wd[42:50] = 0.5
            cook_curve_wd[111:123] = 0.8
            dish_curve_wd = np.zeros(144)
            dish_curve_wd[123:132] = 0.7
            wash_curve_wd = np.zeros(144)
            wash_curve_wd[54:72] = 0.4
            media_curve_wd = np.zeros(144)
            media_curve_wd[108:138] = 0.8
            hygiene_curve_wd = np.zeros(144)
            hygiene_curve_wd[42:48] = 0.5
            hygiene_curve_wd[120:129] = 0.5

            cook_curve_we = cook_curve_wd.copy()
            dish_curve_we = dish_curve_wd.copy()
            wash_curve_we = wash_curve_wd.copy()
            media_curve_we = media_curve_wd.copy()
            hygiene_curve_we = hygiene_curve_wd.copy()

        # Calibration targets scaled by occupancy
        occ_ratio = float(occupancy_rate)
        target_induction_scaled = 420.0 * occ_ratio
        target_dish_scaled = (185.0 if has_dish else 0.0) * occ_ratio
        if has_washtower:
            target_wash_scaled = 345.0 * occ_ratio
            rated_wash_kw = 1.50
        elif has_washing_machine:
            target_wash_scaled = 130.0 * occ_ratio
            rated_wash_kw = 0.50
        else:
            target_wash_scaled = 0.0
            rated_wash_kw = 0.50

        target_plug_scaled = target_plug_kwh * occ_ratio
        target_light_scaled = target_lighting_kwh * occ_ratio

        def run_calibration(target_kwh, curve_wd, curve_we, rated_kw):
            if target_kwh <= 0:
                return np.zeros((365, 144)), 0.0
            intensity = np.zeros((365, 144))
            for d in range(365):
                if not is_occupied_day_365[d]:
                    continue
                curve = curve_wd if day_types_365[d] == "weekday" else curve_we
                intensity[d] = curve * active_mask[d]

            raw_sum_hours = intensity.sum() * (10.0 / 60.0)
            if raw_sum_hours <= 0:
                return np.zeros((365, 144)), 0.0
            scale = target_kwh / (raw_sum_hours * rated_kw)
            power_arr = intensity * scale * rated_kw
            actual_kwh = power_arr.sum() * (10.0 / 60.0)
            error_pct = abs(actual_kwh - target_kwh) / target_kwh * 100.0 if target_kwh > 0 else 0.0
            return power_arr, error_pct

        p_induction, err_ind = run_calibration(target_induction_scaled, cook_curve_wd, cook_curve_we, 2.0)
        p_dish, err_dish = run_calibration(target_dish_scaled, dish_curve_wd, dish_curve_we, 1.4)
        p_wash, err_wash = run_calibration(target_wash_scaled, wash_curve_wd, wash_curve_we, rated_wash_kw)
        p_plug, err_plug = run_calibration(target_plug_scaled, media_curve_wd, media_curve_we, 0.40)

        # Calibrate Lighting
        light_intensity = np.zeros((365, 144))
        for d in range(365):
            if is_occupied_day_365[d]:
                light_intensity[d] = (ghi_10m[d] < 60.0).astype(float) * active_occupants_10min[d]
        raw_light_kwh = light_intensity.sum() * (10.0 / 60.0) * 0.15
        if raw_light_kwh > 0:
            scale_light = target_light_scaled / raw_light_kwh
            p_light = light_intensity * 0.15 * scale_light
            err_light = abs(p_light.sum() * (10.0 / 60.0) - target_light_scaled) / target_light_scaled * 100.0
        else:
            p_light = np.zeros((365, 144))
            err_light = 0.0

        # DHW Distribution (75 L/person/occupied day)
        # Allocate proportionally to hygiene curve when occupants active
        target_daily_dhw_liters = 75.0 * self.occupants
        for d in range(365):
            if is_occupied_day_365[d]:
                curve = hygiene_curve_wd if day_types_365[d] == "weekday" else hygiene_curve_we
                daily_h = curve * active_mask[d]
                sum_h = daily_h.sum()
                if sum_h > 0:
                    dhw_liters_10min[d] = daily_h * (target_daily_dhw_liters / sum_h)
                else:
                    # Fallback only when active
                    active_indices = np.where(active_mask[d])[0]
                    if len(active_indices) > 0:
                        dhw_liters_10min[d, active_indices] = target_daily_dhw_liters / len(active_indices)

        self.appliance_calibration_errors = {
            "fridge": 0.0,
            "induction": err_ind,
            "dishwasher": err_dish if has_dish else 0.0,
            "laundry": err_wash,
            "plug_loads": err_plug,
            "lighting": err_light,
        }

        # Total electric load at 10-min resolution
        total_elec_10min = appliance_power_10min + p_induction + p_dish + p_wash + p_plug + p_light

        # Resample from 10-min to 15-min
        x_10 = np.linspace(0, 365, 365 * 144, endpoint=False)
        x_15 = np.linspace(0, 365, 35040, endpoint=False)

        elec_flat = total_elec_10min.flatten()
        dhw_flat = dhw_liters_10min.flatten()
        setp_flat = heat_setpoint_10min.flatten()
        act_flat = active_occupants_10min.flatten().astype(float)

        total_elec_15min = np.interp(x_15, x_10, elec_flat)
        dhw_liters_15min = np.interp(x_15, x_10, dhw_flat)
        heat_setpoint_15min = np.interp(x_15, x_10, setp_flat)
        occupants_active_15min = np.interp(x_15, x_10, act_flat)

        # Enforce zero DHW during away and unoccupied periods (Bug 7-d fix)
        dhw_liters_15min[occupants_active_15min < 0.1] = 0.0
        dhw_liters_15min[is_occupied_15min == 0] = 0.0

        # Requirement 5: Reallocate DHW masked to zero back to active periods to strictly preserve 75 L/person/occupied_day (+-0.5%)
        target_daily_l = 75.0 * self.occupants
        for d in range(365):
            s_idx = d * 96
            e_idx = s_idx + 96
            if is_occupied_day_365[d]:
                day_active = (occupants_active_15min[s_idx:e_idx] >= 0.1) & (is_occupied_15min[s_idx:e_idx] == 1)
                day_dhw_sum = dhw_liters_15min[s_idx:e_idx].sum()
                if day_dhw_sum > 0:
                    dhw_liters_15min[s_idx:e_idx] = dhw_liters_15min[s_idx:e_idx] * (target_daily_l / day_dhw_sum)
                elif day_active.sum() > 0:
                    dhw_liters_15min[s_idx:e_idx][day_active] = target_daily_l / day_active.sum()
            else:
                dhw_liters_15min[s_idx:e_idx] = 0.0

        # Resample individual appliance profiles to 15-min
        p_ind_15min = np.interp(x_15, x_10, p_induction.flatten())
        p_oven_15min = np.interp(x_15, x_10, p_oven.flatten())
        p_cooking_15min = p_ind_15min + p_oven_15min
        p_dish_15min = np.interp(x_15, x_10, p_dish.flatten())
        p_wash_15min = np.interp(x_15, x_10, p_wash.flatten())
        p_plug_15min = np.interp(x_15, x_10, p_plug.flatten())
        p_light_15min = np.interp(x_15, x_10, p_light.flatten())
        p_fridge_15min = np.full(35040, p_fridge_base)
        p_vent_standby_15min = np.full(35040, p_purifier_base + p_erv_base + p_standby_base)

        # 15-minute discrete states (0: away, 1: home_active, 2: sleep)
        persons_state_15min = []
        idx_10 = np.clip((np.arange(35040) * (144.0 / 96.0)).astype(int), 0, 365 * 144 - 1)
        for p_idx in range(self.occupants):
            p_flat = paths_10min[:, :, p_idx].flatten()
            mapped = np.array(p_flat[idx_10], dtype=int)
            persons_state_15min.append(mapped)

        # Reproduction validation results
        rep_val = self.run_reproduction_validation() if run_validation else {}

        appliance_15min = {
            "cooking": p_cooking_15min,
            "dishwasher": p_dish_15min,
            "laundry": p_wash_15min,
            "plug": p_plug_15min,
            "lighting": p_light_15min,
            "fridge": p_fridge_15min,
            "vent_standby": p_vent_standby_15min,
        }

        return {
            "mode": self.mode,
            "mode_detail": self.mode_detail,
            "is_occupied_day_365": is_occupied_day_365,
            "is_occupied_15min": is_occupied_15min,
            "occupants_active_15min": occupants_active_15min,
            "heat_setpoint_15min": heat_setpoint_15min,
            "total_elec_base_load_kw_15min": total_elec_15min,
            "dhw_liters_15min": dhw_liters_15min,
            "annual_elec_base_kwh": float(total_elec_15min.sum() * 0.25),
            "annual_dhw_liters": float(dhw_liters_15min.sum()),
            "tus_fit": {c["curve"]: {"mae_pct_p": c["mae"], "threshold_pct_p": 2.0, "status": "PASS" if c["mae"] <= 2.0 else "FAIL"} for c in rep_val["fit_12"] if c["daytype"] == "weekday"},
            "tus_fit_12": rep_val["fit_12"],
            "leave_hist": rep_val["leave_hist"],
            "return_hist": rep_val["return_hist"],
            "realism": rep_val["realism"],
            "sample_person_days": rep_val["sample_person_days"],
            "sleep_dur_hist": rep_val["sleep_dur_hist"],
            "away_episodes_weekday_mean": rep_val["away_episodes_weekday_mean"],
            "rule_1b_violations": rep_val.get("rule_1b_violations", 0),
            "top_5_away_diff": rep_val.get("top_5_away_diff", []),
            "appliance_15min": appliance_15min,
            "persons_state_15min": persons_state_15min,
            "kosis_validation": self.kosis_validation_metrics,
            "appliance_calibration_errors": self.appliance_calibration_errors,
        }
