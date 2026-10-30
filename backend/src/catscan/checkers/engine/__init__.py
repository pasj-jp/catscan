"""
CatScan generic rules and primitives engine.
"""
from .primitives import (
    ElementContext,
    register_primitive,
    get_primitive,
)
from .evaluator import (
    evaluate_element,
    evaluate_section,
)

__all__ = [
    "ElementContext",
    "register_primitive",
    "get_primitive",
    "evaluate_element",
    "evaluate_section",
]
