"""
Evaluator for Word rules: applies check primitives to extracted elements.
"""
from typing import Any, Dict, List, Optional, Union

from .primitives import ElementContext, get_primitive
from ..rules.schema import WordCheckRule, WordElementRule, WordSectionRule


DEFAULT_KEYS_BY_PRIMITIVE = {
    "style_contains": "style_ok",
    "style_in": "style_ok",
    "has_cjk": "lang_ok",
    "no_cjk": "lang_ok",
    "uppercase": "lang_ok",
    "forbid_chars": "delimiter_ok",
    "font": "style_ok",
}


def evaluate_element(
    element: Optional[ElementContext],
    rule: WordElementRule,
) -> Dict[str, Any]:
    """Evaluate an element against a WordElementRule."""
    if element is None:
        detail: Dict[str, Any] = {
            "text": rule.missing_text or "未検出 (Missing)",
            "type": rule.type,
            "style": "None",
            "ok": False,
            "notes": rule.missing_message or "未検出",
        }
        for k in rule.scoring_keys:
            detail[k] = False
        return detail

    raw_text = element.text.strip() if rule.strip_text else element.text
    if rule.truncate and len(raw_text) > rule.truncate:
        display_text = raw_text[:rule.truncate] + "..."
    else:
        display_text = raw_text

    detail = {
        "text": display_text,
        "type": rule.type,
        "style": element.style_name,
    }

    # Initialize scoring keys as True
    for k in rule.scoring_keys:
        detail[k] = True

    fail_notes: List[str] = []

    for check in rule.checks:
        prim_fn = get_primitive(check.check)
        if prim_fn is None:
            continue

        target_key = check.key or DEFAULT_KEYS_BY_PRIMITIVE.get(check.check, "style_ok")
        if target_key not in detail:
            detail[target_key] = True

        # Extract arguments relevant to the primitive
        kwargs = check.model_dump(exclude_unset=True)
        kwargs.pop("check", None)
        kwargs.pop("key", None)
        fail_msg = kwargs.pop("fail_message", None)

        try:
            passed = prim_fn(element, **kwargs)
        except Exception:
            passed = False

        if not passed:
            detail[target_key] = False
            if fail_msg and fail_msg not in fail_notes:
                fail_notes.append(fail_msg)

    # Determine overall ok for this element row
    detail["ok"] = all(bool(detail.get(k, True)) for k in rule.scoring_keys)
    detail["notes"] = " / ".join(fail_notes) if fail_notes else (rule.pass_message or "適合")

    # Merge safe style details from Word paragraph
    detail.update(element.style_details)

    return detail


def evaluate_section(
    section_rule: WordSectionRule,
    elements_by_role: Dict[str, Union[Optional[ElementContext], List[ElementContext]]],
) -> Dict[str, Any]:
    """
    Evaluate an entire section against its configured elements and rules.
    Returns the exact dictionary expected by CatScan frontend and scoring.
    """
    details: List[Dict[str, Any]] = []

    for element_rule in section_rule.elements:
        role = element_rule.role
        role_elements = elements_by_role.get(role)

        if isinstance(role_elements, list):
            if not role_elements:
                if element_rule.required:
                    details.append(evaluate_element(None, element_rule))
            else:
                for el in role_elements:
                    details.append(evaluate_element(el, element_rule))
        else:
            details.append(evaluate_element(role_elements, element_rule))

    # All elements must be ok for the section to be ok
    section_ok = all(d.get("ok", False) for d in details) if details else section_rule.empty_is_ok

    out: Dict[str, Any] = {
        "title": section_rule.title,
        "anchor": section_rule.anchor,
        "ok": section_ok,
        "details": details,
        "extra_info": section_rule.extra_info.to_output(),
        "rules": dict(section_rule.rules),
        "extra_rules": list(section_rule.extra_rules),
    }
    if section_rule.message:
        out["message"] = section_rule.message
    return out

