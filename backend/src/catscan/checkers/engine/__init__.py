"""
CatScan generic rules and primitives engine.
"""
from .primitives import (
    ElementContext,
    CheckResult,
    register_primitive,
    get_primitive,
)
from .evaluator import (
    evaluate_element,
    evaluate_section,
)

__all__ = [
    "ElementContext",
    "CheckResult",
    "register_primitive",
    "get_primitive",
    "evaluate_element",
    "evaluate_section",
]
