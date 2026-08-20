from __future__ import annotations

from cw_platform.models.instructions import InstructionSet
from cw_platform.models.output import OutputField
from cw_platform.models.review import ReviewItem
from cw_platform.review.thresholds import ThresholdConfig, get_threshold

# Pseudo field name used to look up the classification threshold for a document
# type; falls back to that type's "default" threshold when not configured.
CLASSIFICATION_FIELD = "classification"


def build_review_queue(
    document_type: str,
    fields: list[OutputField],
    dictionary_required_fields: list[str],
    thresholds: ThresholdConfig,
    *,
    classification_confidence: float | None = None,
    instructions: InstructionSet | None = None,
) -> list[ReviewItem]:
    items: list[ReviewItem] = []
    fields_by_name = {f.name: f for f in fields}

    if classification_confidence is not None:
        threshold = get_threshold(thresholds, document_type, CLASSIFICATION_FIELD)
        if classification_confidence < threshold:
            items.append(
                ReviewItem(
                    field_name=CLASSIFICATION_FIELD,
                    reason="low_confidence",
                    detail=(
                        f"classification confidence {classification_confidence:.2f} "
                        f"below threshold {threshold:.2f}"
                    ),
                )
            )

    if instructions is not None:
        for instruction in instructions.instructions:
            threshold = get_threshold(thresholds, document_type, instruction.field_name)
            if instruction.confidence < threshold:
                items.append(
                    ReviewItem(
                        field_name=instruction.field_name,
                        reason="low_confidence",
                        detail=(
                            f"instruction interpretation confidence {instruction.confidence:.2f} "
                            f"below threshold {threshold:.2f}"
                        ),
                    )
                )

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
