import os
import tempfile
import time
from pathlib import Path
import pytest

from catscan.checkers.engine.primitives import (
    ElementContext,
    check_font,
    check_forbid_chars,
    check_has_cjk,
    check_no_cjk,
    check_style_contains,
    check_uppercase,
)
from catscan.checkers.rules import RulesError, load_rules
from catscan.checkers.rules.schema import WordRules


def test_primitives_cjk():
    el_ja = ElementContext(text="日本加速器学会", style_name="011", style_details={})
    el_en = ElementContext(text="Particle Accelerator Society", style_name="012", style_details={})

    assert check_has_cjk(el_ja) is True
    assert check_no_cjk(el_ja) is False

    assert check_has_cjk(el_en) is False
    assert check_no_cjk(el_en) is True


def test_primitives_forbid_chars():
    el_ok = ElementContext(text="Author A, Author B", style_name="020", style_details={})
    el_bad = ElementContext(text="Author A，Author B", style_name="020", style_details={})

    assert check_forbid_chars(el_ok, chars=["，", "、"]) is True
    assert check_forbid_chars(el_bad, chars=["，", "、"]) is False


def test_primitives_font_tolerance():
    el = ElementContext(
        text="Test",
        style_name="011",
        style_details={
            "font_name": "MS PGothic",
            "font_size": 13.9,
            "alignment": "CENTER",
            "bold": False,
        },
    )

    # Size 13.9 is within 14.0 ± 0.5
    assert check_font(el, size=14.0, size_tolerance=0.5, alignment="CENTER") is True
    # Size 13.9 is NOT within 14.0 ± 0.05
    assert check_font(el, size=14.0, size_tolerance=0.05) is False
    # Alignment mismatch
    assert check_font(el, alignment="JUSTIFY") is False


def test_pasj_word_yaml_loads():
    rules = load_rules("pasj_word", WordRules)
    assert "Title" in rules.sections
    assert "Authors" in rules.sections

    title_sec = rules.sections["Title"]
    assert title_sec.anchor == "title"
    assert len(title_sec.elements) == 2
    assert title_sec.elements[0].role == "jtitle"
    assert title_sec.elements[1].role == "etitle"

    # Verify extra_info.to_output() generates exact HTML headers without raw HTML in YAML
    output = title_sec.extra_info.to_output()
    assert "<thead>" in output["headers"]
    assert "和文タイトル" in title_sec.elements[0].type


def test_word_rules_hot_reload(monkeypatch):
    """Verify that editing the YAML file is hot-reloaded automatically."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_rules_dir = Path(tmpdir)
        yaml_path = tmp_rules_dir / "test_hot.yaml"

        yaml_v1 = """
sections:
  Title:
    title: "Version 1 Title"
    anchor: "title"
    extra_info:
      title: "Breakdown"
      columns: ["type", "text"]
"""
        yaml_path.write_text(yaml_v1, encoding="utf-8")
        monkeypatch.setenv("CATSCAN_RULES_DIR", str(tmp_rules_dir))

        r1 = load_rules("test_hot", WordRules)
        assert r1.sections["Title"].title == "Version 1 Title"

        # Update file content and bump mtime
        time.sleep(0.05)
        yaml_v2 = """
sections:
  Title:
    title: "Version 2 Title (Updated)"
    anchor: "title"
    extra_info:
      title: "Breakdown"
      columns: ["type", "text"]
"""
        yaml_path.write_text(yaml_v2, encoding="utf-8")
        os.utime(yaml_path, (time.time() + 1, time.time() + 1))

        r2 = load_rules("test_hot", WordRules)
        assert r2.sections["Title"].title == "Version 2 Title (Updated)"
