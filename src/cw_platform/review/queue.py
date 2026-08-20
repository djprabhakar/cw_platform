from __future__ import annotations

from cw_platform.models.output import OutputField
from cw_platform.models.review import ReviewItem
from cw_platform.review.thresholds import ThresholdConfig, get_threshold


def build_review_queue(
    document_type: str,
    fields: list[OutputField],
    dictionary_required_fields: list[str],
    thresholds: ThresholdConfig,
) -> list[ReviewItem]:
    items: list[ReviewItem] = []
    fields_by_name = {f.name: f for f in fields}

    for field in fields:
        threshold = get_threshold(thresholds, document_type, field.name)
        if field.confidence < threshold:
            items.append(
                ReviewItem(
                    field_name=field.name,
                    reason="low_confidence",
                    detail=f"confidence {field.confidence:.2f} below threshold {threshold:.2f}",
                )
            )

    for required_name in dictionary_required_fields:
        if required_name not in fields_by_name:
            items.append(
                ReviewItem(
                    field_name=required_name,
                    reason="missing_required_field",
                    detail="required field was not found during mapping or extraction",
                )
            )

    return items
