"""Small, independent mutations for CatScan's manuscript-format audit."""

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile
from zipfile import ZipInfo

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt


EXAMPLES = Path(__file__).resolve().parents[1]
PASJ_WORD, JACOW_WORD, PASJ_LATEX, JACOW_LATEX = "pasj-word", "jacow-word", "pasj-latex", "jacow-latex"
BASELINES = {
    PASJ_WORD: "PASJ_Sample_Paper.docx",
    JACOW_WORD: "JACoW_MSWord_Style_Guide.docx",
    PASJ_LATEX: "latex_pasj_perfect.tex",
    JACOW_LATEX: "latex_jacow_perfect.tex",
}


@dataclass(frozen=True)
class Case:
    group: str
    name: str
    description: str
    expected: str
    mutate: Callable[[bytes], bytes] | None = None
    suffix: str | None = None
    template: str | None = None
    verify_template: bool = False
    source: str | None = None

    @property
    def filename(self) -> Path:
        return Path(self.group) / (self.name + (self.suffix or Path(BASELINES[self.group]).suffix))


def source_bytes(group: str, source: str | None = None) -> bytes:
    data = (EXAMPLES / (source or BASELINES[group])).read_bytes()
    if group == JACOW_LATEX and source is None:
        return data.replace(b"{article}", b"{jacow}", 1)
    return data


def _word(edit):
    def mutate(data):
        doc = Document(BytesIO(data))
        edit(doc)
        result = BytesIO()
        doc.save(result)
        return result.getvalue()
    return mutate


def _tex(edit, encoding="utf-8"):
    return lambda data: edit(data.decode("utf-8")).encode(encoding)


def _replace(text, before, after):
    if before not in text:
        raise ValueError(f"Mutation target missing: {before!r}")
    return text.replace(before, after, 1)


def _all_paragraphs(doc):
    for paragraph in doc.paragraphs:
        yield paragraph
    seen = set()
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell._tc not in seen:
                    seen.add(cell._tc)
                    yield from cell.paragraphs


def _text(doc, snippet):
    return next(p for p in _all_paragraphs(doc) if snippet in p.text)


def _style(doc, prefix):
    return next(p for p in doc.paragraphs if p.text and p.style.name.startswith(prefix))


def _edit_text(paragraph, before, after):
    """Replace visible text without resetting formatting outside the changed span."""
    runs = paragraph.runs
    text = "".join(run.text for run in runs)
    start = text.index(before)
    end = start + len(before)
    offset = 0
    for run in runs:
        run_end = offset + len(run.text)
        if offset < end and run_end > start:
            left = max(0, start - offset)
            right = min(len(run.text), end - offset)
            run.text = run.text[:left] + (after if offset <= start else "") + run.text[right:]
        offset = run_end


def _drop(paragraph):
    paragraph._p.getparent().remove(paragraph._p)


def _duplicate(paragraph):
    paragraph._p.addnext(deepcopy(paragraph._p))


def _set_paper(doc, width, height):
    doc.sections[0].page_width = Mm(width)
    doc.sections[0].page_height = Mm(height)


def _set_columns(doc, attribute, value):
    changed = False
    for section in doc.sections:
        cols = section._sectPr.find(qn("w:cols"))
        if cols is not None and cols.get(qn("w:num")) == "2":
            cols.set(qn(f"w:{attribute}"), value)
            changed = True
    if not changed:
        raise ValueError("No two-column section found in the template")


def _font_size(paragraph, points, *, mixed=False):
    runs = [run for run in paragraph.runs if run.text.strip()]
    if not runs:
        raise ValueError("No visible text runs found")
    if mixed and len(runs) == 1:
        text = runs[0].text
        runs[0].text = text[:10]
        runs.append(paragraph.add_run(text[10:]))
    if mixed:
        correct_size = runs[-1].font.size or paragraph.style.font.size
        if correct_size is None:
            raise ValueError("Cannot determine the normal title size")
        # Keep a direct formatting override at the tail of the paragraph as
        # well, so a checker cannot pass by examining only the last run.
        runs[-1].font.size = correct_size
    for run in (runs[:1] if mixed else runs):
        run.font.size = Pt(points)


def _lower_title(paragraph):
    paragraph.style.font.all_caps = False
    for run in paragraph.runs:
        run.font.all_caps = False
        run.text = run.text.lower()


def _after_abstract(doc):
    next(p for p in doc.paragraphs if p.text.startswith("1.\tはじめに")).insert_paragraph_before(
        "This second abstract paragraph exercises the single-paragraph rule."
    )


def _tracked_text(paragraph):
    insertion = OxmlElement("w:ins")
    insertion.set(qn("w:id"), "1")
    insertion.set(qn("w:author"), "Audit fixture")
    insertion.append(paragraph.runs[0]._r)
    paragraph._p.append(insertion)


def _east_asian_font(paragraph, name):
    for run in paragraph.runs:
        run.font.name = name
        run._r.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)


def _zip(entries):
    result = BytesIO()
    with ZipFile(result, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(ZipInfo(name), content, compress_type=ZIP_DEFLATED)
    return result.getvalue()


def _pasj_zip(data):
    main = data.replace(b"\\maketitle", b"\\maketitle\n\\input{sections/body}", 1)
    return _zip({
        "manuscript/main.tex": main,
        "manuscript/sections/body.tex": "測定した値は，設定値と一致しました。\n".encode(),
    })


def _jacow_bib(data, entries):
    text = data.decode()
    text = _replace(text, r"\usepackage{url}", "\\usepackage{url}\n\\addbibresource{refs.bib}")
    text, count = re.subn(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}", r"\\printbibliography", text, flags=re.S)
    if count != 1:
        raise ValueError("Expected one bibliography block")
    return _zip({"main.tex": text.encode(), **entries})


def word_case(group, name, description, expected, edit):
    return Case(group, name, description, expected, _word(edit))


def tex_case(group, name, description, expected, before, after):
    return Case(group, name, description, expected, _tex(lambda text: _replace(text, before, after)))


CASES = [
    *(Case(group, "baseline", "基线样例", "baseline") for group in BASELINES),
    Case(PASJ_LATEX, "official-style-guide", "PASJ 2026 官方 LaTeX 指南", "baseline", source="PASJ_Sample_Paper.tex"),
    Case(JACOW_LATEX, "official-style-guide", "仓库收录的 JACoW LaTeX 指南", "baseline", source="paper.tex"),
    word_case(PASJ_WORD, "wrong-a4-height", "保留 210 mm 页宽，首页改成 250 mm 高", "Margins.margins_ok",
      lambda d: _set_paper(d, 210, 250)),
    word_case(PASJ_WORD, "letter-paper", "把首页设为 US Letter", "Margins.margins_ok",
      lambda d: _set_paper(d, 215.9, 279.4)),
    word_case(PASJ_WORD, "wrong-top-margin", "把首页上边距改为 25 mm", "Margins.margins_ok",
      lambda d: setattr(d.sections[0], "top_margin", Mm(25))),
    word_case(PASJ_WORD, "single-column-body", "把双栏正文改成单栏", "Margins.col_ok",
      lambda d: _set_columns(d, "num", "1")),
    word_case(PASJ_WORD, "wide-column-gutter", "把正文栏间距改为 10 mm", "Margins.col_ok",
      lambda d: _set_columns(d, "space", "567")),
    word_case(PASJ_WORD, "mixed-title-size", "把英文标题首个文字片段改为 24 pt", "Title.style_ok",
      lambda d: _font_size(_style(d, "012)"), 24, mixed=True)),
    word_case(PASJ_WORD, "left-aligned-title", "把英文标题改为左对齐", "Title.style_ok",
      lambda d: setattr(_style(d, "012)"), "alignment", WD_ALIGN_PARAGRAPH.LEFT)),
    word_case(PASJ_WORD, "missing-english-title", "删除英文标题", "Title.style_ok|Title.lang_ok",
      lambda d: _drop(_style(d, "012)"))),
    word_case(PASJ_WORD, "fullwidth-author-delimiter", "把日文作者分隔符改为全角逗号", "Authors.delimiter_ok",
      lambda d: _edit_text(_style(d, "020)"), ",", "，")),
    word_case(PASJ_WORD, "japanese-abstract", "在英文摘要末尾加日文", "Abstract.lang_ok",
      lambda d: _text(d, "This template has been prepared").add_run(" 日本語の文です。")),
    word_case(PASJ_WORD, "two-abstract-paragraphs", "在第一个正文标题前插入第二段英文摘要", "Abstract.lang_ok",
      _after_abstract),
    word_case(PASJ_WORD, "heading-without-number", "删除第一个章节标题的编号", "Headings.number_ok",
      lambda d: _edit_text(_style(d, "04)"), "1.\t", "")),
    word_case(PASJ_WORD, "large-body-text", "把一个标准正文段落的字号改成 18 pt", "Paragraphs.style_ok",
      lambda d: _font_size(_text(d, "論文執筆にあたっては"), 18)),
    word_case(PASJ_WORD, "japanese-body-punctuation", "在正文中使用全角逗号和句点", "Paragraphs.punct_ok",
      lambda d: _text(d, "論文執筆にあたっては").add_run(" 補足文，測定値を示します．")),
    word_case(PASJ_WORD, "unit-without-space", "在正文使用 3GeV，数字与单位之间没有空格", "Paragraphs.unit_spacing",
      lambda d: _text(d, "論文執筆にあたっては").add_run(" ビームエネルギーは3GeVです。")),
    word_case(PASJ_WORD, "unit-with-nonbreaking-space", "使用符合要求的不间断空格连接 3 和 GeV", "no-new",
      lambda d: _text(d, "論文執筆にあたっては").add_run(" ビームエネルギーは3\u00a0GeVです。")),
    word_case(PASJ_WORD, "mac-hiragino-fallback", "模拟 MS 字体无法正确输出 PDF 时采用官方建议的 Hiragino 字体",
      "no-new", lambda d: _east_asian_font(_style(d, "011)"), "ヒラギノ角ゴ ProN")),
    word_case(PASJ_WORD, "figure-missing-period", "去掉一个英文图题末尾的句号", "Figures.period_ok",
      lambda d: _edit_text(_text(d, "Document layout."), "Document layout.", "Document layout")),
    word_case(PASJ_WORD, "table-title-japanese", "把表题中的英文改为日文", "Tables.lang_ok",
      lambda d: _edit_text(_text(d, "Document Layout"), "Document Layout", "用紙設定")),
    word_case(PASJ_WORD, "missing-cited-reference", "删掉仍被正文引用的第 7 条文献", "References.missing_reference",
      lambda d: _drop(_text(d, "[7]\thttps://en.wikipedia.org"))),
    word_case(PASJ_WORD, "duplicate-reference-number", "复制第 3 条参考文献", "References.duplicate_reference",
      lambda d: _duplicate(_text(d, "[3]\thttp://conference.kek.jp"))),
    word_case(PASJ_WORD, "first-citation-out-of-order", "把第一次引用 [1] 改为 [2, 1]", "References.citation_order",
      lambda d: _edit_text(_text(d, "ホームページ[1]"), "[1]", "[2, 1]")),
    word_case(PASJ_WORD, "typographic-citation-range", "把正文范围 [2-5] 改为全角编号和排版用连接号",
      "no-new", lambda d: _edit_text(_text(d, "[2-5]"), "[2-5]", "［２–５］")),
    word_case(PASJ_WORD, "uncited-reference", "删除正文里唯一一次引用 [14] 的编号", "References.uncited_reference",
      lambda d: _edit_text(_text(d, "[13, 14]"), "[13, 14]", "[13]")),
    word_case(PASJ_WORD, "reference-number-unreadable", "保留第 14 条文献正文，但去掉可读取的编号", "References.unknown_reference_number",
      lambda d: _edit_text(_text(d, "[14]\tO."), "[14]\t", "")),
    word_case(PASJ_WORD, "reference-url-trailing-period", "在参考文献 URL 末尾追加句点", "References.doi_ok",
      lambda d: _text(d, "[5]\thttps://www.pasj.jp").add_run(".")),
    word_case(PASJ_WORD, "tracked-change", "在标题中保留一条未接受的修订", "request.400@Track Changes",
      lambda d: _tracked_text(_style(d, "011)"))),
    word_case(JACOW_WORD, "lowercase-title", "把标题改为小写并关闭全大写显示", "Title.case_ok",
      lambda d: _lower_title(_style(d, "JACoW_Paper Title"))),
    word_case(JACOW_WORD, "large-title", "把整个标题改为 24 pt", "Title.font_size|Title.style_ok|Title.title_style_ok",
      lambda d: _font_size(_style(d, "JACoW_Paper Title"), 24)),
    word_case(JACOW_WORD, "mixed-title-size", "首段设为 24 pt，末段显式保留规范字号",
      "Title.font_size|Title.style_ok|Title.title_style_ok", lambda d: _font_size(_style(d, "JACoW_Paper Title"), 24, mixed=True)),
    word_case(JACOW_WORD, "wrong-page-height", "首页维持原宽，纸张高度改为 250 mm", "Margins.margins_ok",
      lambda d: setattr(d.sections[0], "page_height", Mm(250))),
    word_case(JACOW_WORD, "wrong-left-margin", "把首页左边距改为 30 mm", "Margins.margins_ok",
      lambda d: setattr(d.sections[0], "left_margin", Mm(30))),
    word_case(JACOW_WORD, "single-column-body", "把原有两栏正文改为单栏", "Margins.col_ok",
      lambda d: _set_columns(d, "num", "1")),
    word_case(JACOW_WORD, "figure-missing-period", "去掉 Figure 1 图题末尾句号", "Figures.caption_ok",
      lambda d: _edit_text(_text(d, "Figure 1: The layout"), "paper.", "paper")),
    word_case(JACOW_WORD, "duplicate-figure-number", "复制 Figure 1 的题注", "Figures.unique_ok",
      lambda d: _duplicate(_text(d, "Figure 1: The layout"))),
    word_case(JACOW_WORD, "duplicate-reference", "在文献列表中再插入一个 [1]", "References.unique_ok",
      lambda d: _duplicate(_text(d, "[1]\tJACoW,"))),
    word_case(JACOW_WORD, "dangling-reference", "在正文新增一条无对应文献的 [99] 引用", "References.missing_reference",
      lambda d: _text(d, "These instructions are a typical implementation").add_run(" See [99].")),
    word_case(JACOW_WORD, "abstract-citation", "在 JACoW 摘要里增加文献引用", "Abstract.citation_ok",
      lambda d: _text(d, "Numerous accelerator-related conference series").add_run(" See [1].")),
    Case(JACOW_WORD, "template-mismatch", "选 PASJ 后上传 JACoW Word 原稿", "request.template_mismatch",
         template="pasj", verify_template=True),
    tex_case(PASJ_LATEX, "wrong-class", "把 PASJ 文档类换成 article", "INCORRECT_DOCUMENT_CLASS",
      r"\documentclass{PASJ2026}", r"\documentclass{article}"),
    tex_case(PASJ_LATEX, "missing-japanese-title", "把日文标题命令注释掉", "MISSING_JAPANESE_TITLE", r"\jtitle", r"% \jtitle"),
    tex_case(PASJ_LATEX, "missing-english-title", "把英文标题命令注释掉", "MISSING_ENGLISH_TITLE", r"\title", r"% \title"),
    tex_case(PASJ_LATEX, "japanese-in-english-title", "给英文标题加一段日文", "ENGLISH_TITLE_CONTAINS_JAPANESE",
      "PERFECT COMPLIANT", "日本語 PERFECT COMPLIANT"),
    tex_case(PASJ_LATEX, "fullwidth-author-delimiter", "把日文作者分隔符改为全角逗号", "AUTHORS_DELIMITER_FULLWIDTH",
      r"加速太郎\jaffi{A},", r"加速太郎\jaffi{A}，"),
    tex_case(PASJ_LATEX, "japanese-abstract", "在英文摘要中混入日文", "ABSTRACT_CONTAINS_JAPANESE",
      "This document serves", "日文の文章です。 This document serves"),
    tex_case(PASJ_LATEX, "missing-abstract", "移除摘要命令，保留段落内容", "MISSING_ABSTRACT", r"\Abstract", "% Abstract removed"),
    tex_case(PASJ_LATEX, "body-fullwidth-comma", "把正文里的顿号换成全角逗号", "BODY_PUNCTUATION_COMMA",
      "執筆においては、", "執筆においては，"),
    tex_case(PASJ_LATEX, "body-fullwidth-period", "把正文句号换成全角句点", "BODY_PUNCTUATION_PERIOD",
      "極めて重要です。", "極めて重要です．"),
    tex_case(PASJ_LATEX, "punctuation-in-textbf", "把包含违规全角逗号的正文放入 textbf", "BODY_PUNCTUATION_COMMA",
      "執筆においては、", r"\textbf{執筆においては，}"),
    tex_case(PASJ_LATEX, "caption-japanese", "在图题加入日文", "CAPTION_CONTAINS_JAPANESE",
      "Measured transverse beam", "測定したビーム Measured transverse beam"),
    tex_case(PASJ_LATEX, "caption-missing-period", "去掉图题句号", "FIGURE_CAPTION_MISSING_PERIOD",
      "profile at 3.0~GeV.", "profile at 3.0~GeV"),
    tex_case(PASJ_LATEX, "caption-with-short-form", "声明短图题并在正式图题中放入日文", "CAPTION_CONTAINS_JAPANESE",
      r"\caption{Measured", r"\caption[Beam profile]{日文の図 Measured"),
    tex_case(PASJ_LATEX, "dangling-figure-label", "把正文中的图号指向不存在的 label", "UNDEFINED_REFERENCE",
      r"\ref{fig:profile}", r"\ref{fig:missing}"),
    tex_case(PASJ_LATEX, "doi-trailing-period", "在 DOI 结尾加入句点", "DOI_ENDS_IN_PERIOD",
      "PASJ2021-MOP001}", "PASJ2021-MOP001.}"),
    tex_case(PASJ_LATEX, "commented-example", "在注释中加入全角标点和一个伪图题", "no-new",
      r"\maketitle", "\\maketitle\n% 説明，確認． \\caption{和文。}"),
    tex_case(PASJ_LATEX, "punctuation-in-math", "在数学模式中使用全角逗号，验证正文标点规则的上下文", "no-new",
      r"\maketitle", "\\maketitle\n$ x，y $"),
    Case(PASJ_LATEX, "cp932-source", "用 CP932 保存，并在正文加入全角逗号", "BODY_PUNCTUATION_COMMA",
         _tex(lambda text: _replace(text, "執筆においては、", "執筆においては，"), "cp932")),
    Case(PASJ_LATEX, "included-body-fault", "压缩包的子文件包含违规标点", "BODY_PUNCTUATION_COMMA@sections/body.tex",
         _pasj_zip, ".zip"),
    tex_case(PASJ_LATEX, "missing-input", "引用一个未提交的 TeX 子文件", "coverage@Could not read TeX input",
      r"\maketitle", "\\maketitle\n\\input{missing-section}"),
    tex_case(JACOW_LATEX, "citation-etal", "取消 et al. 的斜体命令", "ET_AL_NOT_WRAPPED", r"\emph{et al.}", "et al."),
    tex_case(JACOW_LATEX, "doi-extra-space", "在 doi: 和 DOI 之间插空格", "DOI_CONTAINS_SPACE", "doi:10.", "doi: 10."),
    tex_case(JACOW_LATEX, "doi-no-prefix", "删除 DOI 的 doi: 前缀", "NO_DOI_PREFIX", "doi:10.", "10."),
    tex_case(JACOW_LATEX, "doi-as-url", "改用 https://doi.org/ 链接", "DOI_IS_URL", "doi:10.", "https://doi.org/10."),
    tex_case(JACOW_LATEX, "volume-and-issue", "使用 Vol. X, Issue X, 格式", "VOLUME_ISSUE", "vol. 22, no. 4,", "Vol. 22, Issue 4,"),
    tex_case(JACOW_LATEX, "wrong-class", "把 jacow 文档类改为 article", "INCORRECT_DOCUMENT_CLASS",
      "{jacow}", "{article}"),
    tex_case(JACOW_LATEX, "abstract-citation", "在摘要末尾插入文献引用", "ABSTRACT_CITATION",
      r"\end{abstract}", "See \\cite{ref_valid_1}.\n\\end{abstract}"),
    tex_case(JACOW_LATEX, "missing-figure-caption", "注释掉图题", "MISSING_FIGURE_CAPTION",
      r"\caption{Measured", r"% \caption{Measured"),
    tex_case(JACOW_LATEX, "dangling-figure-label", "把图引用改为不存在的 label", "UNDEFINED_REFERENCE",
      r"\ref{fig1}", r"\ref{missing-fig}"),
    tex_case(JACOW_LATEX, "missing-citation-key", "内联参考文献中无对应的引用键", "UNDEFINED_CITATION",
      r"\cite{ref_valid_1, ref_valid_2}", r"\cite{ref_missing}"),
    Case(JACOW_LATEX, "missing-bib-file", "使用 BibLaTeX，但没有上传文献库", "coverage@refs.bib",
         lambda data: _jacow_bib(data, {}), ".zip"),
    Case(JACOW_LATEX, "external-bib-key-missing", "文献库只有第一个引用键", "coverage@ref_valid_2",
         lambda data: _jacow_bib(data, {"refs.bib": b"@article{ref_valid_1, title={Test}}\n"}), ".zip"),
    Case(JACOW_LATEX, "japanese-comment-auto", "英文稿附带日文注释，自动识别应仍为 JACoW", "template.jacow",
         _tex(lambda text: "% 日本語のメモ\n" + text), template="auto"),
]


def generate_samples(output: Path) -> None:
    for case in CASES:
        base = source_bytes(case.group, case.source)
        data = case.mutate(base) if case.mutate else base
        if case.mutate is not None and data == base:
            raise ValueError(f"Mutation did not change {case.filename}")
        path = output / "samples" / case.filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
