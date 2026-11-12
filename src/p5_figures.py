"""Small accessible SVG chart helpers for Phase 5; no plotting packages required."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

PALETTE = {
    "blue": "#2563eb",
    "teal": "#0f766e",
    "orange": "#d97706",
    "red": "#b91c1c",
    "purple": "#7c3aed",
    "gray": "#64748b",
    "light": "#cbd5e1",
    "green": "#15803d",
}


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _wrapped(text: str, width: int = 135) -> list[str]:
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def write_horizontal_bars(
    path: Path,
    *,
    title: str,
    description: str,
    subtitle: str,
    labels: list[str],
    series: list[dict[str, Any]],
    axis_label: str,
    interpretation: str,
    limitation: str,
    x_max: float | None = None,
) -> dict[str, Any]:
    width = 1100
    left, right = 235, 1055
    plot_width = right - left
    row_height = 27
    plot_top = 160
    plot_bottom = plot_top + row_height * max(1, len(labels))
    footer_lines = _wrapped("Interpretation: " + interpretation, 145)
    limit_lines = _wrapped("Limitation: " + limitation, 145)
    height = plot_bottom + 78 + 18 * (len(footer_lines) + len(limit_lines))
    values = [
        float(value)
        for entry in series
        for value in entry.get("values", [])
    ]
    maximum = x_max if x_max is not None else max(values, default=1.0)
    if maximum <= 0:
        maximum = 1.0
    legend = "  ".join(str(entry["name"]) for entry in series)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f"<title id=\"title\">{_esc(title)}</title>",
        f"<desc id=\"desc\">{_esc(description)}</desc>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="34" y="42" font-family="sans-serif" font-size="24" font-weight="700">{_esc(title)}</text>',
        f'<text x="34" y="70" font-family="sans-serif" font-size="13" fill="#334155">{_esc(subtitle)}</text>',
    ]
    legend_x = left
    for entry in series:
        color = entry.get("color", PALETTE["blue"])
        parts.append(
            f'<rect x="{legend_x}" y="91" width="13" height="13" fill="{_esc(color)}"/>'
        )
        parts.append(
            f'<text x="{legend_x + 19}" y="102" font-family="sans-serif" font-size="12">{_esc(entry["name"])}</text>'
        )
        legend_x += max(140, 8 * len(str(entry["name"])) + 48)
    for tick in range(5):
        fraction = tick / 4
        x = left + plot_width * fraction
        value = maximum * fraction
        parts.append(
            f'<line x1="{x:.2f}" y1="{plot_top - 5}" x2="{x:.2f}" y2="{plot_bottom}" stroke="#e2e8f0"/>'
        )
        parts.append(
            f'<text x="{x:.2f}" y="{plot_bottom + 19}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="11" fill="#475569">{value:.3g}</text>'
        )
    for index, label in enumerate(labels):
        y = plot_top + index * row_height + row_height / 2
        parts.append(
            f'<text x="{left - 12}" y="{y + 4:.2f}" text-anchor="end" '
            f'font-family="sans-serif" font-size="11" fill="#334155">{_esc(label)}</text>'
        )
        series_count = max(1, len(series))
        bar_height = min(10, (row_height - 4) / series_count)
        for series_index, entry in enumerate(series):
            values_for_series = entry.get("values", [])
            value = float(values_for_series[index]) if index < len(values_for_series) else 0.0
            bar_y = (
                plot_top + index * row_height + 2
                + series_index * (bar_height + 2)
            )
            bar_width = max(0.0, min(plot_width, value / maximum * plot_width))
            parts.append(
                f'<rect x="{left}" y="{bar_y:.2f}" width="{bar_width:.2f}" '
                f'height="{bar_height:.2f}" fill="{_esc(entry.get("color", PALETTE["blue"]))}"/>'
            )
    parts.append(
        f'<text x="{left + plot_width / 2}" y="{plot_bottom + 45}" text-anchor="middle" '
        f'font-family="sans-serif" font-size="12" fill="#334155">{_esc(axis_label)}</text>'
    )
    footer_y = plot_bottom + 70
    for label_text, lines in (
        ("Interpretation:", footer_lines),
        ("Limitation:", limit_lines),
    ):
        for line in lines:
            parts.append(
                f'<text x="34" y="{footer_y}" font-family="sans-serif" font-size="12" fill="#334155">{_esc(line)}</text>'
            )
            footer_y += 18
    parts.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return {
        "title": title,
        "description": description,
        "subtitle": subtitle,
        "axis_label": axis_label,
        "legend": legend,
        "interpretation": interpretation,
        "limitation": limitation,
        "path": str(path),
    }


def write_scatter(
    path: Path,
    *,
    title: str,
    description: str,
    subtitle: str,
    points: list[dict[str, Any]],
    x_label: str,
    y_label: str,
    x_max: float,
    interpretation: str,
    limitation: str,
) -> dict[str, Any]:
    width, height = 1040, 650
    left, right, top, bottom = 100, 995, 150, 475
    plot_width, plot_height = right - left, bottom - top
    footer_lines = _wrapped("Interpretation: " + interpretation, 145)
    limit_lines = _wrapped("Limitation: " + limitation, 145)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f"<title id=\"title\">{_esc(title)}</title>",
        f"<desc id=\"desc\">{_esc(description)}</desc>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="34" y="42" font-family="sans-serif" font-size="24" font-weight="700">{_esc(title)}</text>',
        f'<text x="34" y="70" font-family="sans-serif" font-size="13" fill="#334155">{_esc(subtitle)}</text>',
        f'<rect x="{left}" y="105" width="13" height="13" fill="{PALETTE["green"]}"/>',
        f'<text x="{left + 19}" y="116" font-family="sans-serif" font-size="12">Meets all prespecified thresholds</text>',
        f'<rect x="{left + 270}" y="105" width="13" height="13" fill="{PALETTE["gray"]}"/>',
        f'<text x="{left + 289}" y="116" font-family="sans-serif" font-size="12">Does not meet all thresholds</text>',
    ]
    x_max = max(x_max, 0.01)
    for tick in range(5):
        fraction = tick / 4
        x = left + plot_width * fraction
        y = bottom - plot_height * fraction
        parts.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{bottom}" stroke="#e2e8f0"/>'
        )
        parts.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" stroke="#e2e8f0"/>'
        )
        parts.append(
            f'<text x="{x:.2f}" y="{bottom + 20}" text-anchor="middle" font-family="sans-serif" '
            f'font-size="11" fill="#475569">{fraction * x_max:.1%}</text>'
        )
        parts.append(
            f'<text x="{left - 10}" y="{y + 4:.2f}" text-anchor="end" font-family="sans-serif" '
            f'font-size="11" fill="#475569">{fraction:.0%}</text>'
        )
    for point in points:
        x_value = max(0.0, min(x_max, float(point["x"])))
        y_value = max(0.0, min(1.0, float(point["y"])))
        x = left + x_value / x_max * plot_width
        y = bottom - y_value * plot_height
        color = PALETTE["green"] if point["eligible"] else PALETTE["gray"]
        parts.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.5" fill="{color}" fill-opacity="0.75"/>'
        )
    parts.extend(
        [
            f'<text x="{left + plot_width / 2}" y="{bottom + 45}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="12">{_esc(x_label)}</text>',
            f'<text x="24" y="{top + plot_height / 2}" text-anchor="middle" '
            f'transform="rotate(-90 24 {top + plot_height / 2})" font-family="sans-serif" '
            f'font-size="12">{_esc(y_label)}</text>',
        ]
    )
    footer_y = 548
    for lines in (footer_lines, limit_lines):
        for line in lines:
            parts.append(
                f'<text x="34" y="{footer_y}" font-family="sans-serif" font-size="12" fill="#334155">{_esc(line)}</text>'
            )
            footer_y += 18
    parts.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return {
        "title": title,
        "description": description,
        "subtitle": subtitle,
        "x_label": x_label,
        "y_label": y_label,
        "legend": "Eligible / not eligible under all prespecified thresholds",
        "interpretation": interpretation,
        "limitation": limitation,
        "path": str(path),
    }
