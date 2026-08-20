from __future__ import annotations

from pathlib import Path

import yaml

from cw_platform.models.dictionary import DataDictionary, FieldDef

_DICT_DIR = Path(__file__).parent / "dictionaries"


def load_data_dictionary(document_type: str, template: str) -> DataDictionary:
    path = _DICT_DIR / f"{document_type}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No data dictionary for document type: {document_type}")

    raw = yaml.safe_load(path.read_text())
    base_fields = {f["name"]: f for f in raw["fields"]}

    if template != "base":
        overrides = raw.get("overrides", {})
        if template not in overrides:
            raise KeyError(f"No override template '{template}' for document type '{document_type}'")
        for override_field in overrides[template]:
            base_fields[override_field["name"]] = override_field

    fields = [FieldDef(**f) for f in base_fields.values()]
    return DataDictionary(document_type=document_type, template=template, fields=fields)
