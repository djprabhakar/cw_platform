from __future__ import annotations

ThresholdConfig = dict[str, dict[str, object]]

GLOBAL_FALLBACK_THRESHOLD = 0.85

DEFAULT_THRESHOLDS: ThresholdConfig = {
    "bank_statement": {
        "default": 0.85,
        "fields": {"ending_balance": 0.92},
    },
    "agent_bank_notice_interest_payment": {
        "default": 0.85,
        "fields": {"payment_amount": 0.92},
    },
}


def get_threshold(config: ThresholdConfig, document_type: str, field_name: str) -> float:
    type_config = config.get(document_type)
    if type_config is None:
        return GLOBAL_FALLBACK_THRESHOLD

    field_thresholds: dict[str, float] = type_config.get("fields", {})  # type: ignore[assignment]
    if field_name in field_thresholds:
        return field_thresholds[field_name]

    return type_config.get("default", GLOBAL_FALLBACK_THRESHOLD)  # type: ignore[return-value]
