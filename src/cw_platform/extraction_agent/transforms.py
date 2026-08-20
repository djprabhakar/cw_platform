from __future__ import annotations

from datetime import datetime


class UnknownTransformError(Exception):
    pass


def apply_transform(raw_text: str, transformation: str | None) -> str:
    if transformation is None or transformation == "none":
        return raw_text

    if transformation == "strip_commas":
        return raw_text.replace(",", "")

    if transformation == "multiply_by_1000":
        cleaned = raw_text.replace(",", "").replace("$", "")
        value = float(cleaned) * 1000
        return f"{value:.2f}"

    if transformation == "parse_date_mmddyyyy":
        parsed = datetime.strptime(raw_text, "%m/%d/%Y")
        return parsed.strftime("%Y-%m-%d")

    raise UnknownTransformError(f"Unknown transformation: {transformation}")
