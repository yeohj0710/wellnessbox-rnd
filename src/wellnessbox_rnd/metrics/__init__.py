"""Metrics and metadata helpers."""

from importlib import import_module

__all__ = [
    "PRODomainFormSchemaV1",
    "PROFormResponseV1",
    "PROFormSchemaV1",
    "PROItemSchemaV1",
    "build_default_pro_form_schema_v1",
    "summarize_pro_form_contract_v1",
    "validate_pro_form_response_v1",
]


def __getattr__(name: str):
    if name in __all__:
        module = import_module("wellnessbox_rnd.metrics.pro_scoring")
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

