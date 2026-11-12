"""Memory-conscious, neutral-label analysis of processed sleep-minute records."""

from __future__ import annotations

import csv
import sqlite3
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator


EXPECTED_COLUMNS = ["id", "date", "value", "log_id", "calendar_date"]
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
OVERNIGHT_END_HOUR = 12
OVERNIGHT_START_LATE_HOUR = 18
OVERNIGHT_START_EARLY_HOUR = 6
MAX_OVERNIGHT_SPAN_MINUTES = 12 * 60


def parse_iso_timestamp(value: str) -> datetime:
    return datetime.strptime(value, TIMESTAMP_FORMAT)


def iter_episodes(records: Iterable[tuple[str, str, str, str]]) -> Iterator[dict]:
    """Aggregate sorted (id, log_id, timestamp, value) records into log episodes."""
    current_key: tuple[str, str] | None = None
    session: dict | None = None

    def finish(item: dict) -> dict:
        start: datetime = item["start"]
        end: datetime = item["end"]
        span_seconds = (end - start).total_seconds()
        span_minutes = span_seconds / 60
        flags = []
        if item["gap_intervals"]:
            flags.append("timestamp_gap_over_60_seconds")
        if item["nonminute_intervals"]:
            flags.append("interval_not_60_seconds")
        if span_minutes > MAX_OVERNIGHT_SPAN_MINUTES:
            flags.append("elapsed_span_over_12_hours")
        if 12 <= start.hour < 18:
            flags.append("afternoon_start_candidate")
        if end.hour >= OVERNIGHT_END_HOUR:
            flags.append("ends_at_or_after_noon")
        crosses_midnight = start.date() != end.date()
        overnight_time_candidate = (
            end.hour < OVERNIGHT_END_HOUR
            and (
                start.hour >= OVERNIGHT_START_LATE_HOUR
                or start.hour < OVERNIGHT_START_EARLY_HOUR
            )
            and span_minutes <= MAX_OVERNIGHT_SPAN_MINUTES
            and item["gap_intervals"] == 0
            and item["nonminute_intervals"] == 0
        )
        category_counts = dict(sorted(item["categories"].items()))
        category_shares = {
            category: count / item["record_count"]
            for category, count in category_counts.items()
        }
        result = {
            "id": item["id"],
            "log_id": item["log_id"],
            "start_timestamp": start.strftime(TIMESTAMP_FORMAT),
            "end_timestamp": end.strftime(TIMESTAMP_FORMAT),
            "waking_date": end.date().isoformat(),
            "recorded_minute_count": item["record_count"],
            "elapsed_span_minutes": span_minutes,
            "crosses_midnight": crosses_midnight,
            "start_hour": start.hour,
            "end_hour": end.hour,
            "gap_intervals_over_60_seconds": item["gap_intervals"],
            "intervals_not_60_seconds": item["nonminute_intervals"],
            "category_counts": category_counts,
            "category_shares": category_shares,
            "quality_flags": flags,
            "overnight_time_candidate": overnight_time_candidate,
            "overnight_candidate": overnight_time_candidate,
            "primary_eligible": False,
            "primary_exclusion_reason": "",
            "_start": start,
            "_end": end,
        }
        return result

    for participant_id, log_id, timestamp, value in records:
        key = (participant_id, log_id)
        moment = (
            timestamp
            if isinstance(timestamp, datetime)
            else parse_iso_timestamp(timestamp)
        )
        if key != current_key:
            if session is not None:
                yield finish(session)
            current_key = key
            session = {
                "id": participant_id,
                "log_id": log_id,
                "start": moment,
                "end": moment,
                "record_count": 0,
                "gap_intervals": 0,
                "nonminute_intervals": 0,
                "categories": Counter(),
            }
        else:
            interval = (moment - session["end"]).total_seconds()
            if interval > 60:
                session["gap_intervals"] += 1
            if interval != 60:
                session["nonminute_intervals"] += 1
            session["end"] = moment
        session["record_count"] += 1
        session["categories"][value] += 1
    if session is not None:
        yield finish(session)


def identify_overlaps(episodes: list[dict]) -> list[dict]:
    """Flag every episode that overlaps another episode for the same participant."""
    ordered = sorted(episodes, key=lambda item: (item["id"], item["_start"], item["log_id"]))
    active_by_participant: dict[str, list[dict]] = defaultdict(list)
    for episode in ordered:
        active = active_by_participant[episode["id"]]
        active[:] = [prior for prior in active if prior["_end"] >= episode["_start"]]
        for prior in active:
            if episode["_start"] <= prior["_end"] and prior["_start"] <= episode["_end"]:
                if "overlaps_another_log" not in prior["quality_flags"]:
                    prior["quality_flags"].append("overlaps_another_log")
                if "overlaps_another_log" not in episode["quality_flags"]:
                    episode["quality_flags"].append("overlaps_another_log")
        active.append(episode)
    return episodes


def assign_primary_eligibility(episodes: list[dict]) -> dict:
    candidates_by_date: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for episode in episodes:
        if episode["overnight_candidate"]:
            candidates_by_date[(episode["id"], episode["waking_date"])].append(episode)

    ambiguous_dates = {
        key for key, items in candidates_by_date.items() if len(items) > 1
    }
    for key in ambiguous_dates:
        for episode in candidates_by_date[key]:
            if "multiple_overnight_logs_same_waking_date" not in episode["quality_flags"]:
                episode["quality_flags"].append("multiple_overnight_logs_same_waking_date")

    for episode in episodes:
        if not episode["overnight_candidate"]:
            if "afternoon_start_candidate" in episode["quality_flags"]:
                episode["primary_exclusion_reason"] = "potential_daytime_or_afternoon_session"
            elif "elapsed_span_over_12_hours" in episode["quality_flags"]:
                episode["primary_exclusion_reason"] = "elapsed_span_over_12_hours"
            elif "ends_at_or_after_noon" in episode["quality_flags"]:
                episode["primary_exclusion_reason"] = "ends_at_or_after_noon"
            else:
                episode["primary_exclusion_reason"] = "start_time_not_in_overnight_window"
            continue
        if (episode["id"], episode["waking_date"]) in ambiguous_dates:
            episode["primary_exclusion_reason"] = "multiple_overnight_logs_same_waking_date"
        elif "overlaps_another_log" in episode["quality_flags"]:
            episode["primary_exclusion_reason"] = "overlapping_log"
        elif episode["gap_intervals_over_60_seconds"] or episode["intervals_not_60_seconds"]:
            episode["primary_exclusion_reason"] = "irregular_timestamp_intervals"
        else:
            episode["primary_eligible"] = True

    return {
        "overnight_candidate_count": sum(bool(e["overnight_candidate"]) for e in episodes),
        "primary_eligible_episode_count": sum(bool(e["primary_eligible"]) for e in episodes),
        "multiple_overnight_waking_dates": len(ambiguous_dates),
        "sessions_on_multiple_overnight_waking_dates": sum(
            len(items) for key, items in candidates_by_date.items() if key in ambiguous_dates
        ),
    }


def analyze_sleep_csv(path: Path) -> dict:
    """Read one processed sleep file, aggregate in SQLite, and return compact outputs."""
    if not path.is_file():
        raise FileNotFoundError(path)
    category_counts: Counter[str] = Counter()
    coverage: dict[str, dict] = {}
    raw_rows = 0
    duplicate_rows = 0
    conflicting_duplicate_rows = 0
    calendar_date_mismatches = 0

    with tempfile.TemporaryDirectory(prefix="fitinsight-p3-sleep-") as temp_dir:
        database = Path(temp_dir) / "sleep.sqlite"
        connection = sqlite3.connect(database)
        try:
            connection.execute("PRAGMA journal_mode=OFF")
            connection.execute("PRAGMA synchronous=OFF")
            connection.execute(
                "CREATE TABLE sleep_records ("
                "id TEXT NOT NULL, log_id TEXT NOT NULL, timestamp TEXT NOT NULL, "
                "value TEXT NOT NULL, PRIMARY KEY(id, log_id, timestamp))"
            )
            with path.open("r", encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                if reader.fieldnames != EXPECTED_COLUMNS:
                    raise ValueError(
                        f"Unexpected sleep columns: {reader.fieldnames!r}; "
                        f"expected {EXPECTED_COLUMNS!r}"
                    )
                for row in reader:
                    raw_rows += 1
                    participant_id = row["id"]
                    log_id = row["log_id"]
                    moment = parse_iso_timestamp(row["date"])
                    if not participant_id or not log_id:
                        raise ValueError("Sleep row is missing id or log_id")
                    if row["calendar_date"] != moment.date().isoformat():
                        calendar_date_mismatches += 1
                    category_counts[row["value"]] += 1
                    cursor = connection.execute(
                        "INSERT OR IGNORE INTO sleep_records VALUES (?, ?, ?, ?)",
                        (participant_id, log_id, row["date"], row["value"]),
                    )
                    if cursor.rowcount == 0:
                        duplicate_rows += 1
                        existing = connection.execute(
                            "SELECT value FROM sleep_records "
                            "WHERE id=? AND log_id=? AND timestamp=?",
                            (participant_id, log_id, row["date"]),
                        ).fetchone()
                        if existing is not None and existing[0] != row["value"]:
                            conflicting_duplicate_rows += 1
                    part = coverage.setdefault(
                        participant_id,
                        {"id": participant_id, "records": 0, "logs": set(),
                         "first_timestamp": row["date"], "last_timestamp": row["date"]},
                    )
                    part["records"] += 1
                    part["logs"].add(log_id)
                    part["first_timestamp"] = min(part["first_timestamp"], row["date"])
                    part["last_timestamp"] = max(part["last_timestamp"], row["date"])

            connection.commit()
            connection.execute(
                "CREATE INDEX sleep_episode_order "
                "ON sleep_records(id, log_id, timestamp)"
            )
            records = connection.execute(
                "SELECT id, log_id, timestamp, value FROM sleep_records "
                "ORDER BY id, log_id, timestamp"
            )
            episodes = list(iter_episodes(records))
            distinct_rows = connection.execute(
                "SELECT COUNT(*) FROM sleep_records"
            ).fetchone()[0]
            distinct_log_ids = connection.execute(
                "SELECT COUNT(DISTINCT log_id) FROM sleep_records"
            ).fetchone()[0]
            reused_log_ids = connection.execute(
                "SELECT COUNT(*) FROM (SELECT log_id FROM sleep_records "
                "GROUP BY log_id HAVING COUNT(DISTINCT id)>1)"
            ).fetchone()[0]
        finally:
            connection.close()

    identify_overlaps(episodes)
    eligibility = assign_primary_eligibility(episodes)
    for participant in coverage.values():
        participant["logs"] = len(participant["logs"])

    metrics = {
        "input_file": str(path),
        "input_rows": raw_rows,
        "distinct_rows": distinct_rows,
        "duplicate_key_rows_after_preprocessing": duplicate_rows,
        "conflicting_duplicate_rows": conflicting_duplicate_rows,
        "participants": len(coverage),
        "distinct_log_id_values": distinct_log_ids,
        "participant_log_groups": len(episodes),
        "log_ids_reused_across_participants": reused_log_ids,
        "timestamp_to_calendar_date_mismatches": calendar_date_mismatches,
        "value_category_counts": dict(sorted(category_counts.items())),
        "cross_midnight_logs": sum(bool(e["crosses_midnight"]) for e in episodes),
        "logs_over_12_hours": sum(
            "elapsed_span_over_12_hours" in e["quality_flags"] for e in episodes
        ),
        "potential_afternoon_start_logs": sum(
            "afternoon_start_candidate" in e["quality_flags"] for e in episodes
        ),
        "logs_with_timestamp_gap_over_60_seconds": sum(
            e["gap_intervals_over_60_seconds"] > 0 for e in episodes
        ),
        "logs_with_non_60_second_intervals": sum(
            e["intervals_not_60_seconds"] > 0 for e in episodes
        ),
        "overlapping_log_count": sum(
            "overlaps_another_log" in e["quality_flags"] for e in episodes
        ),
        **eligibility,
        "interpretation": (
            "Value categories are reported as their stored codes only; their sleep-state "
            "meaning is not established by repository documentation."
        ),
    }
    return {
        "metrics": metrics,
        "episodes": episodes,
        "participant_coverage": sorted(coverage.values(), key=lambda item: item["id"]),
    }


def strip_internal_episode_fields(episode: dict) -> dict:
    """Return serializable episode fields without datetime helper objects."""
    return {key: value for key, value in episode.items() if not key.startswith("_")}
