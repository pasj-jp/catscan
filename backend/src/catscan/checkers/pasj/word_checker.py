import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from docx import Document
from docx.text.paragraph import Paragraph

from ..common.docx_utils import open_docx, doc_metadata, to_element
from ..common.layout import check_sections
from ..common.score import score
from ..engine import evaluate_section
from ..registry import CJK_RE
from ..rules import load_rules
from ..rules.schema import WordRules, WordSectionRule


@dataclass
class PasjParts:
    jtitle_p: Optional[Paragraph] = None
    etitle_p: Optional[Paragraph] = None
    jauthor_p: List[Paragraph] = field(default_factory=list)
    eauthor_p: List[Paragraph] = field(default_factory=list)
    abstract_heading_p: Optional[Paragraph] = None
    abstract_p: List[Paragraph] = field(default_factory=list)
    body_p: List[Paragraph] = field(default_factory=list)
    heading_p: List[Paragraph] = field(default_factory=list)
    ref_heading_p: Optional[Paragraph] = None
    ref_p: List[Paragraph] = field(default_factory=list)
    fig_cap_p: List[Paragraph] = field(default_factory=list)
    tbl_cap_p: List[Paragraph] = field(default_factory=list)


def classify_paragraphs(doc: Document) -> PasjParts:
    parts = PasjParts()
    seen_abstract = False
    seen_refs = False
    seen_caption_elements = set()

    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue

        style_name = p.style.name if p.style else ""

        if "参考文献見出し" in style_name or text == "参考文献" or text.lower() == "references":
            seen_refs = True
            parts.ref_heading_p = p
            continue

        if seen_refs:
            parts.ref_p.append(p)
            continue

        if "Abstract" in style_name or text.lower() == "abstract":
            seen_abstract = True
            parts.abstract_heading_p = p
            continue

        if not seen_abstract:
            if "和文タイトル" in style_name or "011" in style_name:
                if parts.jtitle_p is None:
                    parts.jtitle_p = p
                    continue
            if "英文タイトル" in style_name or "012" in style_name:
                if parts.etitle_p is None:
                    parts.etitle_p = p
                    continue
            if "著者" in style_name or "020" in style_name or "author" in style_name.lower():
                if CJK_RE.search(text):
                    parts.jauthor_p.append(p)
                else:
                    parts.eauthor_p.append(p)
                continue
            if parts.jtitle_p is None and CJK_RE.search(text):
                parts.jtitle_p = p
            elif parts.etitle_p is None and parts.jtitle_p is not None and not CJK_RE.search(text) and not ("著者" in style_name or "author" in style_name.lower()):
                parts.etitle_p = p
            elif CJK_RE.search(text):
                parts.jauthor_p.append(p)
            else:
                parts.eauthor_p.append(p)
        else:
            if len(parts.abstract_p) == 0 and not ("見出し" in style_name or "heading" in style_name.lower()):
                parts.abstract_p.append(p)
                continue

            if "謝辞見出し" in style_name or "063" in style_name or text == "謝辞":
                continue
            elif "章見出し" in style_name or "節見出し" in style_name or "項見出し" in style_name or re.match(r"^\d+(?:\.\d+)*\.?\s", text):
                if not ("箇条書き" in style_name or "07" in style_name):
                    parts.heading_p.append(p)
                else:
                    parts.body_p.append(p)
            elif ("図タイトル" in style_name or re.match(r"^(?:Figure|Fig\.)[\s\xa0]*\d+\s*[:.]", text, re.IGNORECASE)) and not re.match(r"^\([a-z0-9]+\)", text, re.IGNORECASE):
                parts.fig_cap_p.append(p)
                seen_caption_elements.add(id(p._p))
            elif "表タイトル" in style_name or re.match(r"^Table[\s\xa0]*\d+\s*[:.]", text, re.IGNORECASE):
                parts.tbl_cap_p.append(p)
                seen_caption_elements.add(id(p._p))
            else:
                parts.body_p.append(p)

    for t in doc.tables:
        seen_cells = set()
        for r in t.rows:
            for c in r.cells:
                if id(c._tc) in seen_cells:
                    continue
                seen_cells.add(id(c._tc))
                for p in c.paragraphs:
                    if id(p._p) in seen_caption_elements:
                        continue
                    text = p.text.strip()
                    if not text:
                        continue
                    style_name = p.style.name if p.style else ""
                    if re.match(r"^\([a-z0-9]+\)", text, re.IGNORECASE):
                        continue
                    if "図タイトル" in style_name or re.match(r"^(?:Figure|Fig\.)[\s\xa0]*\d+\s*[:.]", text, re.IGNORECASE):
                        parts.fig_cap_p.append(p)
                        seen_caption_elements.add(id(p._p))
                    elif "表タイトル" in style_name or re.match(r"^Table[\s\xa0]*\d+\s*[:.]", text, re.IGNORECASE):
                        parts.tbl_cap_p.append(p)
                        seen_caption_elements.add(id(p._p))

    return parts


def build_paragraphs_section(body_p: List[Paragraph], rule: WordSectionRule) -> Dict[str, Any]:
    fullwidth_commas = 0
    fullwidth_periods = 0
    correct_punct = 0
    comma_examples: List[str] = []
    period_examples: List[str] = []

    for p in body_p:
        t = p.text.strip()
        c_cnt = t.count("，")
        p_cnt = t.count("．")
        fullwidth_commas += c_cnt
        fullwidth_periods += p_cnt
        correct_punct += t.count("、") + t.count("。")
        if c_cnt > 0 and len(comma_examples) < 2:
            comma_examples.append(t[:45] + ("..." if len(t) > 45 else ""))
        if p_cnt > 0 and len(period_examples) < 2:
            period_examples.append(t[:45] + ("..." if len(t) > 45 else ""))

    punct_ok = (fullwidth_commas == 0 and fullwidth_periods == 0)
    comma_status = "問題なし (0 箇所)"
    if fullwidth_commas > 0:
        ex_str = f" — 例: 「{comma_examples[0]}」" if comma_examples else ""
        comma_status = f"和文原稿では使用禁止 ({fullwidth_commas} 箇所検出{ex_str})。「、」に置換してください"

    period_status = "問題なし (0 箇所)"
    if fullwidth_periods > 0:
        ex_str = f" — 例: 「{period_examples[0]}」" if period_examples else ""
        period_status = f"和文原稿では使用禁止 ({fullwidth_periods} 箇所検出{ex_str})。「。」に置換してください"

    para_details = [
        {
            "item": "全角句読点（「、」「。」）",
            "count": f"{correct_punct} 箇所",
            "status": "推奨書式（公用文・PASJ規定準拠）",
            "punct_ok": True,
        },
        {
            "item": "全角カンマ（「，」）",
            "count": f"{fullwidth_commas} 箇所",
            "status": comma_status,
            "punct_ok": fullwidth_commas == 0,
        },
        {
            "item": "全角ピリオド（「．」）",
            "count": f"{fullwidth_periods} 箇所",
            "status": period_status,
            "punct_ok": fullwidth_periods == 0,
        },
    ]

    return {
        "title": rule.title,
        "ok": punct_ok,
        "details": para_details,
        "extra_info": rule.extra_info.to_output(),
        "rules": dict(rule.rules),
        "extra_rules": list(rule.extra_rules),
        "anchor": rule.anchor,
    }


def build_margins_section(doc: Document, rule: WordSectionRule) -> Dict[str, Any]:
    sections = check_sections(doc)
    margins_ok = all(s["margins_ok"] and s["col_ok"] for s in sections)
    return {
        "title": rule.title,
        "extra_rules": list(rule.extra_rules),
        "extra_info": rule.extra_info.to_output(),
        "ok": margins_ok,
        "message": rule.message or "Margins",
        "details": sections,
        "anchor": rule.anchor,
    }


def build_styles_section(doc: Document, rule: WordSectionRule, required_styles: List[str]) -> Dict[str, Any]:
    doc_styles = [s.name for s in doc.styles if s.name]
    style_details = [
        {"style": s, "style_ok": s in doc_styles}
        for s in required_styles
    ]
    return {
        "title": rule.title,
        "ok": all(d.get("style_ok") for d in style_details),
        "details": style_details,
        "extra_info": rule.extra_info.to_output(),
        "rules": dict(rule.rules),
        "extra_rules": list(rule.extra_rules),
        "anchor": rule.anchor,
    }


def build_summary(parts: PasjParts, doc: Document, rules: WordRules) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}

    summary["Title"] = evaluate_section(
        rules.sections["Title"],
        {
            "jtitle": to_element(parts.jtitle_p) if parts.jtitle_p else None,
            "etitle": to_element(parts.etitle_p) if parts.etitle_p else None,
        },
    )

    summary["Authors"] = evaluate_section(
        rules.sections["Authors"],
        {
            "jauthor": [to_element(p) for p in parts.jauthor_p],
            "eauthor": [to_element(p) for p in parts.eauthor_p],
        },
    )

    summary["Abstract"] = evaluate_section(
        rules.sections["Abstract"],
        {
            "heading": to_element(parts.abstract_heading_p) if parts.abstract_heading_p else None,
            "body": [to_element(p) for p in parts.abstract_p],
        },
    )

    summary["Headings"] = evaluate_section(
        rules.sections["Headings"],
        {"heading": [to_element(p) for p in parts.heading_p]},
    )

    summary["Paragraphs"] = build_paragraphs_section(parts.body_p, rules.sections["Paragraphs"])

    summary["Figures"] = evaluate_section(
        rules.sections["Figures"],
        {"figure": [to_element(p) for p in parts.fig_cap_p]},
    )

    summary["Tables"] = evaluate_section(
        rules.sections["Tables"],
        {"table": [to_element(p) for p in parts.tbl_cap_p]},
    )

    summary["References"] = evaluate_section(
        rules.sections["References"],
        {"reference": [to_element(p) for p in parts.ref_p]},
    )

    summary["Margins"] = build_margins_section(doc, rules.sections["Margins"])

    summary["Styles"] = build_styles_section(doc, rules.sections["Styles"], rules.required_styles)

    return summary


class PasjWordChecker:
    """
    PASJ Japanese Word document validator.
    Inspects Microsoft Word (.docx) documents for Japanese Accelerator Society (PASJ)
    2026 guidelines.
    """

    def check(
        self,
        data: bytes,
        filename: str = "document.docx",
    ) -> Dict[str, Any]:
        doc = open_docx(data)
        parts = classify_paragraphs(doc)
        rules = load_rules("pasj_word", WordRules)
        summary = build_summary(parts, doc, rules)
        scores = score(summary)

        return {
            "scores": scores,
            "summary": summary,
            "metadata": doc_metadata(doc),
            "filename": filename,
        }

    def validate(
        self,
        file_source: Any,
        filename: str = "document.docx",
        conference_id: Any = None,
    ) -> Dict[str, Any]:
        data = file_source if isinstance(file_source, bytes) else (
            file_source.getvalue() if hasattr(file_source, "getvalue") else open(file_source, "rb").read()
        )
        return self.check(data, filename=filename)
