"""Deterministic, dependency-free SVG figures for Phase 3."""

from __future__ import annotations

import html
import math
from datetime import date
from pathlib import Path
from typing import Any


PALETTE = {
    "cyan": "#61A9BD",
    "yellow": "#CED14E",
    "green": "#44986D",
    "pink": "#DD83C9",
    "blue": "#1F74AD",
    "orange": "#E98E2E",
    "purple": "#9267C6",
    "brown": "#8D6C5B",
    "red": "#D8524F",
    "grey": "#979797",
    "dark": "#17324D",
    "muted": "#5E7184",
    "grid": "#E5ECF1",
    "paper": "#FFFFFF",
}


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


class Svg:
    def __init__(self, title: str, subtitle: str, note: str, width: int = 1120, height: int = 720):
        self.width = width
        self.height = height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">',
            f"<title>{esc(title)}</title>",
            f"<desc>{esc(subtitle)}. {esc(note)}</desc>",
            f'<rect x="0" y="0" width="{width}" height="{height}" fill="{PALETTE["paper"]}"/>',
            f'<text x="72" y="58" font-family="Arial, sans-serif" font-size="28" '
            f'font-weight="700" fill="{PALETTE["dark"]}">{esc(title)}</text>',
            f'<text x="72" y="91" font-family="Arial, sans-serif" font-size="15" '
            f'fill="{PALETTE["muted"]}">{esc(subtitle)}</text>',
        ]
        self.note = note

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str, width: float = 1, dash: str = ""):
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{color}" stroke-width="{width}"{dash_attr}/>'
        )

    def rect(self, x: float, y: float, width: float, height: float, fill: str, rx: float = 0, stroke: str = "none"):
        self.parts.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" '
            f'rx="{rx:.2f}" fill="{fill}" stroke="{stroke}"/>'
        )

    def circle(self, x: float, y: float, radius: float, fill: str, opacity: float = 1):
        self.parts.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" fill="{fill}" '
            f'fill-opacity="{opacity:.2f}"/>'
        )

    def path(self, points: list[tuple[float, float]], stroke: str, width: float = 2, opacity: float = 1):
        if not points:
            return
        d = " ".join(
            ("M" if index == 0 else "L") + f" {x:.2f} {y:.2f}"
            for index, (x, y) in enumerate(points)
        )
        self.parts.append(
            f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{width}" '
            f'stroke-linecap="round" stroke-linejoin="round" stroke-opacity="{opacity:.2f}"/>'
        )

    def text(
        self,
        x: float,
        y: float,
        value: Any,
        size: int = 13,
        color: str | None = None,
        anchor: str = "start",
        weight: str = "400",
        rotate: float | None = None,
    ):
        color = color or PALETTE["muted"]
        transform = f' transform="rotate({rotate:.1f} {x:.2f} {y:.2f})"' if rotate is not None else ""
        self.parts.append(
            f'<text x="{x:.2f}" y="{y:.2f}" font-family="Arial, sans-serif" '
            f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
            f'fill="{color}"{transform}>{esc(value)}</text>'
        )

    def footer(self):
        self.line(72, self.height - 58, self.width - 72, self.height - 58, PALETTE["grid"], 1)
        self.text(72, self.height - 32, self.note, 12)
        self.parts.append("</svg>")
        return "\n".join(self.parts) + "\n"


def nice_max(value: float) -> float:
    if value <= 0:
        return 1
    exponent = 10 ** math.floor(math.log10(value))
    fraction = value / exponent
    step = 1 if fraction <= 1 else 2 if fraction <= 2 else 5 if fraction <= 5 else 10
    return step * exponent


def y_axis(svg: Svg, x: float, y: float, width: float, height: float, maximum: float, ticks: int = 5):
    top = y
    bottom = y + height
    for index in range(ticks + 1):
        value = maximum * index / ticks
        yy = bottom - height * index / ticks
        svg.line(x, yy, x + width, yy, PALETTE["grid"], 1)
        svg.text(x - 12, yy + 4, f"{value:,.0f}", 12, anchor="end")
    svg.line(x, top, x, bottom, PALETTE["muted"], 1)
    svg.line(x, bottom, x + width, bottom, PALETTE["muted"], 1)


def histogram(values: list[float], bins: int = 12, maximum: float | None = None):
    maximum = maximum or max(values, default=1)
    maximum = max(maximum, 1)
    width = maximum / bins
    counts = [0] * bins
    for value in values:
        index = min(int(value / width), bins - 1)
        counts[max(index, 0)] += 1
    return counts, width, maximum


def step_histogram(rows: list[dict], output_dir: Path) -> dict:
    values = [float(row["total_steps"]) for row in rows if row["total_steps"] is not None]
    counts, bin_width, max_value = histogram(values, bins=12, maximum=30000)
    maximum_count = nice_max(max(counts, default=1))
    svg = Svg(
        "Daily step counts are right-skewed",
        "Distribution across recorded participant-days",
        f"n={len(values)} participant-days; 2,500-step bins; historical records, not a population estimate.",
    )
    x, y, width, height = 104, 150, 930, 410
    y_axis(svg, x, y, width, height, maximum_count)
    bar_width = width / len(counts)
    for index, count in enumerate(counts):
        bar_height = height * count / maximum_count
        bx = x + index * bar_width + 3
        svg.rect(bx, y + height - bar_height, bar_width - 6, bar_height, PALETTE["cyan"], 4)
        if index % 2 == 0:
            svg.text(bx + (bar_width - 6) / 2, y + height + 23, f"{int(index * bin_width / 1000)}k", 12, anchor="middle")
    svg.text(x + width / 2, y + height + 50, "Recorded steps per participant-day", 14, anchor="middle")
    svg.text(34, y + height / 2, "Participant-day records", 13, rotate=-90, anchor="middle")
    path = output_dir / "01_daily_steps_distribution.svg"
    path.write_text(svg.footer(), encoding="utf-8")
    return {
        "file": path.name,
        "title": "Daily step counts are right-skewed",
        "sample_count": len(values),
        "interpretation": "Most recorded days fall in lower step-count bins with a right tail.",
        "size_bytes": path.stat().st_size,
    }


def completeness_histogram(rows: list[dict], output_dir: Path) -> dict:
    groups = {
        "Complete": [float(r["total_steps"]) for r in rows if r["is_complete_day"] is True],
        "Incomplete": [float(r["total_steps"]) for r in rows if r["is_complete_day"] is False],
    }
    maximum = 30000
    bins = 10
    bin_width = maximum / bins
    counts = {}
    for label, values in groups.items():
        series, _, _ = histogram(values, bins=bins, maximum=maximum)
        counts[label] = series
    y_max = nice_max(max(max(v) for v in counts.values()))
    svg = Svg(
        "Step-count distributions differ by completeness",
        "Participant-day counts by recorded-step bin",
        f"Complete n={len(groups['Complete'])}; incomplete n={len(groups['Incomplete'])}; "
        "completeness means 1,440 recorded minutes, not valid/invalid behavior.",
    )
    x, y, width, height = 112, 150, 910, 400
    y_axis(svg, x, y, width, height, y_max)
    category_width = width / bins
    each = category_width * 0.36
    colors = {"Complete": PALETTE["blue"], "Incomplete": PALETTE["orange"]}
    for index in range(bins):
        center = x + (index + 0.5) * category_width
        for shift, label in ((-each / 2, "Complete"), (each / 2, "Incomplete")):
            count = counts[label][index]
            bar_height = height * count / y_max
            svg.rect(
                center + shift - each / 2,
                y + height - bar_height,
                each - 2,
                bar_height,
                colors[label],
                3,
            )
        if index % 2 == 0:
            svg.text(center, y + height + 23, f"{int(index * bin_width / 1000)}k", 12, anchor="middle")
    legend_y = 127
    for index, label in enumerate(("Complete", "Incomplete")):
        lx = 770 + index * 145
        svg.rect(lx, legend_y - 12, 14, 14, colors[label], 3)
        svg.text(lx + 22, legend_y, label, 13)
    svg.text(x + width / 2, y + height + 50, "Recorded steps per participant-day", 14, anchor="middle")
    svg.text(34, y + height / 2, "Participant-day records", 13, rotate=-90, anchor="middle")
    path = output_dir / "02_steps_by_completeness.svg"
    path.write_text(svg.footer(), encoding="utf-8")
    return {
        "file": path.name,
        "title": "Step-count distributions differ by completeness",
        "sample_count": sum(map(len, groups.values())),
        "interpretation": "The two day groups have different distributions; the filter is a sensitivity comparison.",
        "size_bytes": path.stat().st_size,
    }


def daily_trend_coverage(rows: list[dict], output_dir: Path) -> dict:
    by_date: dict[date, list[dict]] = {}
    for row in rows:
        by_date.setdefault(row["activity_date"], []).append(row)
    summary = [
        {
            "date": day,
            "mean": sum(r["total_steps"] for r in group) / len(group),
            "participants": len({r["id"] for r in group}),
        }
        for day, group in sorted(by_date.items())
    ]
    svg = Svg(
        "Daily step averages need their coverage context",
        "Mean recorded steps and distinct participants per calendar date",
        f"{len(rows)} participant-days across {len(summary)} dates; the daily cohort changes over time.",
    )
    x, w = 105, 920
    top_y, top_h = 155, 245
    bottom_y, bottom_h = 450, 100
    max_steps = nice_max(max(item["mean"] for item in summary))
    y_axis(svg, x, top_y, w, top_h, max_steps)
    points = []
    for index, item in enumerate(summary):
        px = x + (index / max(len(summary) - 1, 1)) * w
        py = top_y + top_h - (item["mean"] / max_steps) * top_h
        points.append((px, py))
    svg.path(points, PALETTE["blue"], 3)
    for px, py in points[::4]:
        svg.circle(px, py, 3.5, PALETTE["blue"])
    svg.text(x, top_y - 16, "Mean recorded steps", 14, weight="700", color=PALETTE["dark"])
    participants_max = max(item["participants"] for item in summary)
    svg.line(x, bottom_y + bottom_h, x + w, bottom_y + bottom_h, PALETTE["muted"], 1)
    for index, item in enumerate(summary):
        cell_width = w / len(summary)
        bar_height = bottom_h * item["participants"] / max(participants_max, 1)
        svg.rect(
            x + index * cell_width + 1,
            bottom_y + bottom_h - bar_height,
            max(cell_width - 2, 1),
            bar_height,
            PALETTE["green"],
            1,
        )
    svg.text(x, bottom_y - 14, "Distinct participant coverage", 14, weight="700", color=PALETTE["dark"])
    svg.text(x, bottom_y + bottom_h + 25, summary[0]["date"].strftime("%b %d"), 12)
    svg.text(x + w, bottom_y + bottom_h + 25, summary[-1]["date"].strftime("%b %d"), 12, anchor="end")
    svg.text(x + w / 2, bottom_y + bottom_h + 25, "2016 observation dates", 12, anchor="middle")
    path = output_dir / "03_daily_steps_and_coverage.svg"
    path.write_text(svg.footer(), encoding="utf-8")
    return {
        "file": path.name,
        "title": "Daily step averages need their coverage context",
        "sample_count": len(rows),
        "interpretation": "Date-level means should be read alongside the changing participant count.",
        "size_bytes": path.stat().st_size,
    }


def paired_weekday_svg(participant_rows: list[dict], output_dir: Path) -> dict:
    valid = [
        row for row in participant_rows
        if row["weekday_mean_total_steps"] is not None
        and row["weekend_mean_total_steps"] is not None
    ]
    values = [
        row["weekday_mean_total_steps"] for row in valid
    ] + [
        row["weekend_mean_total_steps"] for row in valid
    ]
    maximum = nice_max(max(values, default=1))
    svg = Svg(
        "Weekend and weekday means vary by participant",
        "Paired participant mean steps, with one line per participant",
        f"{len(valid)} participants have both weekday and weekend records; direction is descriptive.",
    )
    x, y, width, height = 150, 155, 820, 390
    y_axis(svg, x, y, width, height, maximum)
    x1, x2 = x + 135, x + width - 55
    svg.text(x1, y + height + 34, "Weekday", 14, anchor="middle", weight="700")
    svg.text(x2, y + height + 34, "Weekend", 14, anchor="middle", weight="700")
    positive = negative = equal = 0
    for row in valid:
        a = row["weekday_mean_total_steps"]
        b = row["weekend_mean_total_steps"]
        y1 = y + height - a / maximum * height
        y2 = y + height - b / maximum * height
        color = (
            PALETTE["blue"] if b > a
            else PALETTE["orange"] if b < a
            else PALETTE["grey"]
        )
        positive += b > a
        negative += b < a
        equal += b == a
        svg.line(x1, y1, x2, y2, color, 2, dash="4 3" if b == a else "")
        svg.circle(x1, y1, 3.5, color)
        svg.circle(x2, y2, 3.5, color)
    legend_y = 127
    for index, (label, color) in enumerate((
        ("Weekend mean higher", PALETTE["blue"]),
        ("Weekday mean higher", PALETTE["orange"]),
        ("Equal", PALETTE["grey"]),
    )):
        lx = 560 + index * 160
        svg.line(lx, legend_y - 4, lx + 20, legend_y - 4, color, 3)
        svg.text(lx + 27, legend_y, label, 12)
    svg.text(32, y + height / 2, "Mean recorded steps", 13, rotate=-90, anchor="middle")
    path = output_dir / "04_weekday_weekend_paired_steps.svg"
    path.write_text(svg.footer(), encoding="utf-8")
    return {
        "file": path.name,
        "title": "Weekend and weekday means vary by participant",
        "sample_count": len(valid),
        "interpretation": f"Weekend mean higher for {positive}; weekday higher for {negative}; equal for {equal}.",
        "size_bytes": path.stat().st_size,
    }


def composition_svg(rows: list[dict], output_dir: Path) -> dict:
    fields = [
        ("very_active_minutes", "Very active", PALETTE["cyan"]),
        ("fairly_active_minutes", "Fairly active", PALETTE["yellow"]),
        ("lightly_active_minutes", "Lightly active", PALETTE["green"]),
        ("sedentary_minutes", "Sedentary", PALETTE["blue"]),
    ]
    groups = {
        "Incomplete": [r for r in rows if r["is_complete_day"] is False],
        "Complete": [r for r in rows if r["is_complete_day"] is True],
    }
    percentages = {}
    for label, group in groups.items():
        component_shares = {name: [] for _, name, _ in fields}
        for row in group:
            values = [row[field] for field, _, _ in fields]
            denominator = sum(value for value in values if value is not None)
            if denominator <= 0:
                continue
            for (field, name, _), value in zip(fields, values):
                component_shares[name].append(100 * value / denominator)
        percentages[label] = {
            name: sum(items) / len(items) if items else 0
            for name, items in component_shares.items()
        }
    svg = Svg(
        "Recorded-time composition differs by completeness",
        "Mean within-day share of the four activity-minute fields",
        "Per-day denominator is very + fairly + lightly active + sedentary minutes; it is not verified waking time.",
    )
    x, y, height = 210, 160, 390
    bar_width = 190
    for center, label in ((x + 130, "Incomplete"), (x + 500, "Complete")):
        svg.line(center - 70, y + height, center + 70, y + height, PALETTE["muted"], 1)
        bottom = y + height
        for _, name, color in fields:
            amount = percentages[label][name]
            segment_height = height * amount / 100
            svg.rect(center - bar_width / 2, bottom - segment_height, bar_width, segment_height, color, 0)
            if segment_height >= 20:
                svg.text(center, bottom - segment_height / 2 + 5, f"{amount:.1f}%", 13, color=PALETTE["dark"], anchor="middle", weight="700")
            bottom -= segment_height
        svg.text(center, y + height + 32, label, 15, color=PALETTE["dark"], anchor="middle", weight="700")
    for index, (_, name, color) in enumerate(fields):
        lx = 690
        ly = 190 + index * 43
        svg.rect(lx, ly - 13, 16, 16, color, 3)
        svg.text(lx + 26, ly, name, 13)
    svg.text(45, y + height / 2, "Share of four recorded fields (%)", 13, rotate=-90, anchor="middle")
    svg.text(x, y + height + 69, f"n={len(groups['Incomplete'])} incomplete days", 12)
    svg.text(x + 370, y + height + 69, f"n={len(groups['Complete'])} complete days", 12)
    path = output_dir / "05_activity_minute_composition.svg"
    path.write_text(svg.footer(), encoding="utf-8")
    return {
        "file": path.name,
        "title": "Recorded-time composition differs by completeness",
        "sample_count": len(rows),
        "interpretation": (
            "The composition denominator is the sum of four recorded minute fields; "
            f"sedentary share is {percentages['Complete']['Sedentary']:.1f}% for complete "
            f"and {percentages['Incomplete']['Sedentary']:.1f}% for incomplete days."
        ),
        "size_bytes": path.stat().st_size,
    }


def heatmap_color(value: float | None) -> str:
    if value is None:
        return "#D9E0E5"
    if value <= -0.5:
        return "#2672A6"
    if value < 0:
        return "#8AB1CC"
    if value == 0:
        return "#FFFFFF"
    if value < 0.5:
        return "#FAB770"
    return "#E99F2E"


def correlation_heatmap(correlations: dict, output_dir: Path) -> dict:
    heat = correlations["heatmap"]
    labels = heat["labels"]
    cells = heat["cells"]
    size = 80
    x0, y0 = 350, 170
    svg = Svg(
        "Activity measures show varied rank associations",
        "Spearman correlations across participant-days",
        "Each tile shows Spearman rho and valid pair count; associations are descriptive and repeated days are not independent people.",
        width=1120,
        height=800,
    )
    for index, label in enumerate(labels):
        svg.text(x0 - 13, y0 + index * size + size / 2 + 4, label, 13, anchor="end")
        svg.text(x0 + index * size + size / 2, y0 - 13, label, 12, anchor="middle", rotate=-40)
    for cell in cells:
        x = x0 + cell["x_index"] * size
        y = y0 + cell["y_index"] * size
        value = cell["spearman"]
        svg.rect(x, y, size - 2, size - 2, heatmap_color(value), 5, PALETTE["paper"])
        number = "NA" if value is None else f"{value:.2f}"
        svg.text(x + (size - 2) / 2, y + 42, number, 14, anchor="middle", color=PALETTE["dark"], weight="700")
        svg.text(x + (size - 2) / 2, y + 64, f"n={cell['n_pairs']}", 11, anchor="middle")
    legend_y = y0 + len(labels) * size + 18
    for index, (label, color) in enumerate((
        ("≤ −0.5", "#2672A6"),
        ("−0.5 to 0", "#8AB1CC"),
        ("0", "#FFFFFF"),
        ("0 to 0.5", "#FAB770"),
        ("≥ 0.5", "#E99F2E"),
        ("Missing", "#D9E0E5"),
    )):
        lx = 270 + index * 110
        svg.rect(lx, legend_y, 22, 18, color, 2, PALETTE["grid"])
        svg.text(lx + 29, legend_y + 14, label, 11)
    path = output_dir / "06_activity_correlation_heatmap.svg"
    path.write_text(svg.footer(), encoding="utf-8")
    return {
        "file": path.name,
        "title": "Activity measures show varied rank associations",
        "sample_count": max((cell["n_pairs"] for cell in cells), default=0),
        "interpretation": "The matrix reports rank associations and per-cell sample sizes.",
        "size_bytes": path.stat().st_size,
    }


def sleep_episode_histogram(episodes: list[dict], output_dir: Path) -> dict:
    values = [float(episode["recorded_minute_count"]) for episode in episodes]
    counts, bin_width, maximum = histogram(values, bins=12, maximum=960)
    y_max = nice_max(max(counts, default=1))
    svg = Svg(
        "Recorded sleep-log sizes vary",
        "Number of rows recorded within each participant-log group",
        f"n={len(values)} logs; x-axis counts minute records, not validated sleep duration; 12 bins.",
    )
    x, y, width, height = 110, 155, 920, 400
    y_axis(svg, x, y, width, height, y_max)
    bar_width = width / len(counts)
    for index, count in enumerate(counts):
        bh = height * count / y_max
        bx = x + index * bar_width + 3
        svg.rect(bx, y + height - bh, bar_width - 6, bh, PALETTE["purple"], 4)
        if index % 2 == 0:
            svg.text(bx + (bar_width - 6) / 2, y + height + 22, f"{int(index * bin_width)}", 11, anchor="middle")
    svg.text(x + width / 2, y + height + 50, "Recorded sleep-minute rows per log", 14, anchor="middle")
    svg.text(35, y + height / 2, "Participant-log episodes", 13, rotate=-90, anchor="middle")
    path = output_dir / "07_recorded_sleep_log_sizes.svg"
    path.write_text(svg.footer(), encoding="utf-8")
    return {
        "file": path.name,
        "title": "Recorded sleep-log sizes vary",
        "sample_count": len(values),
        "interpretation": "Session row counts vary; they are not labeled as actual minutes asleep.",
        "size_bytes": path.stat().st_size,
    }


def sleep_activity_scatter(matched_rows: list[dict], output_dir: Path) -> dict:
    rows = [
        row for row in matched_rows
        if row["sleep_match_status"] == "matched"
        and row["recorded_sleep_minutes"] is not None
        and row["total_steps"] is not None
    ]
    x_values = [float(row["recorded_sleep_minutes"]) for row in rows]
    y_values = [float(row["total_steps"]) for row in rows]
    max_x = nice_max(max(x_values, default=1))
    max_y = nice_max(max(y_values, default=1))
    svg = Svg(
        "Recorded sleep-log rows and waking-day steps",
        "One point per unique eligible participant-waking date",
        f"n={len(rows)} matched dates; recorded log rows are not validated sleep duration; no causal interpretation.",
    )
    x, y, width, height = 120, 155, 900, 400
    y_axis(svg, x, y, width, height, max_y)
    for index in range(6):
        value = max_x * index / 5
        xx = x + width * index / 5
        svg.line(xx, y + height, xx, y + height + 5, PALETTE["muted"], 1)
        svg.text(xx, y + height + 22, f"{value:.0f}", 11, anchor="middle")
    for x_value, y_value in zip(x_values, y_values):
        px = x + width * x_value / max_x
        py = y + height - height * y_value / max_y
        svg.circle(px, py, 4, PALETTE["cyan"], opacity=0.72)
    svg.text(x + width / 2, y + height + 50, "Recorded sleep-minute rows in episode", 14, anchor="middle")
    svg.text(37, y + height / 2, "Waking-day recorded steps", 13, rotate=-90, anchor="middle")
    path = output_dir / "08_sleep_records_vs_waking_steps.svg"
    path.write_text(svg.footer(), encoding="utf-8")
    return {
        "file": path.name,
        "title": "Recorded sleep-log rows and waking-day steps",
        "sample_count": len(rows),
        "interpretation": "Each point is a unique matched waking date; the chart is descriptive only.",
        "size_bytes": path.stat().st_size,
    }


def generate_figures(
    *,
    rows: list[dict],
    weekday_participant_rows: list[dict],
    correlations: dict,
    sleep_episodes: list[dict],
    matched_rows: list[dict],
    output_dir: Path,
) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if not weekday_participant_rows:
        raise ValueError("Weekday participant pairs are required for the paired figure")

    return [
        step_histogram(rows, output_dir),
        completeness_histogram(rows, output_dir),
        daily_trend_coverage(rows, output_dir),
        paired_weekday_svg(weekday_participant_rows, output_dir),
        composition_svg(rows, output_dir),
        correlation_heatmap(correlations, output_dir),
        sleep_episode_histogram(sleep_episodes, output_dir),
        sleep_activity_scatter(matched_rows, output_dir),
    ]
