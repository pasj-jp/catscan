#!/usr/bin/env python3
"""
Create a new Indico conference event with all 9 JACoW & PASJ Word/LaTeX
example manuscripts from the example/ directory.

Usage inside the Indico virtual environment on the host:
  sudo -u indico env INDICO_CONFIG=/opt/indico/etc/indico.conf /opt/indico/.venv/bin/python scripts/populate_indico_papers.py
"""
import os
import json
from datetime import datetime, timedelta
import pytz
from flask import session
from indico.web.flask.app import make_app

# Locate example directory
DEFAULT_EXAMPLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "example"))
EXAMPLE_DIR = os.environ.get("CATSCAN_EXAMPLE_DIR", DEFAULT_EXAMPLE_DIR)
if not os.path.exists(EXAMPLE_DIR) and os.path.exists("/opt/catscan/example"):
    EXAMPLE_DIR = "/opt/catscan/example"

app = make_app()
with app.app_context(), app.test_request_context():
    from indico.core.db import db
    from indico.modules.users import User
    from indico.modules.categories.models.categories import Category
    from indico.modules.events import Event
    from indico.modules.events.operations import create_event
    from indico.modules.events.models.events import EventType
    from indico.modules.events.models.persons import EventPerson
    from indico.modules.events.features.util import set_feature_enabled
    from indico.modules.events.contributions.operations import create_contribution
    from indico.modules.events.contributions.models.persons import ContributionPersonLink, AuthorType
    from indico.modules.events.editing.models.editable import Editable, EditableType
    from indico.modules.events.editing.models.revisions import EditingRevision
    from indico.modules.events.editing.models.file_types import EditingFileType
    from indico.modules.events.editing.models.revision_files import EditingRevisionFile
    from indico.modules.files.models.files import File

    ev1 = Event.get(1)
    admin = (
        User.query.filter_by(is_admin=True, is_deleted=False, is_system=False).first()
        or (ev1.creator if ev1 else None)
        or User.query.filter_by(is_deleted=False, is_system=False).first()
    )
    author = User.query.filter(~User.is_deleted, User.email == "author@catscan.local").first() or admin
    session.set_session_user(admin)

    root_cat = Category.get_root()
    now = datetime.now(pytz.timezone("Asia/Tokyo")).replace(minute=0, second=0, microsecond=0)
    start_dt = now + timedelta(days=7)
    end_dt = start_dt + timedelta(days=3)

    event = create_event(
        root_cat,
        EventType.conference,
        {
            "creator": admin,
            "title": "PASJ & JACoW 2026 Automated Paper Validation Benchmark Conference",
            "start_dt": start_dt,
            "end_dt": end_dt,
            "timezone": "Asia/Tokyo",
            "description": (
                "End-to-end validation benchmark conference for CatScan + Indico integration "
                "(PASJ 2026 Japanese & JACoW English Word/LaTeX templates)."
            ),
        },
        add_creator_as_manager=True,
    )
    db.session.flush()

    for feat in ("papers", "editing"):
        try:
            set_feature_enabled(event, feat, True)
        except Exception:
            pass
    db.session.flush()

    src_ft = EditingFileType.query.filter_by(
        event=event, type=EditableType.paper, name="Editable Source (Word / LaTeX)"
    ).first()
    if not src_ft:
        src_ft = EditingFileType(
            event=event,
            name="Editable Source (Word / LaTeX)",
            extensions=["docx", "doc", "tex", "bib", "cls", "sty", "zip", "tar.gz"],
            allow_multiple_files=True,
            required=True,
            publishable=False,
            type=EditableType.paper,
        )
        db.session.add(src_ft)
        db.session.flush()

    person = EventPerson.for_user(author, event)
    if not person.id:
        db.session.add(person)
    db.session.commit()

    papers = [
        {
            "code": "MOP001",
            "title": "JACoW MS-Word Style Guide (Clean Benchmark)",
            "description": "Standard JACoW compliant Word manuscript test case (0 title errors).",
            "file": os.path.join(EXAMPLE_DIR, "JACoW_MSWord_Style_Guide.docx"),
            "filename": "MOP001_JACoW_MSWord_Style_Guide.docx",
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
        {
            "code": "MOP002",
            "title": "JACoW Word Formatting Issues Test Paper",
            "description": "JACoW Word manuscript with intentional title capitalization errors.",
            "file": os.path.join(EXAMPLE_DIR, "word_jacow_issues.docx"),
            "filename": "MOP002_word_jacow_issues.docx",
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
        {
            "code": "MOP003",
            "title": "JACoW LaTeX Sample Paper (Clean Benchmark)",
            "description": "Standard JACoW compliant LaTeX manuscript test case (0 issues).",
            "file": os.path.join(EXAMPLE_DIR, "latex_jacow_perfect.tex"),
            "filename": "MOP003_latex_jacow_perfect.tex",
            "content_type": "application/x-tex",
        },
        {
            "code": "MOP004",
            "title": "JACoW LaTeX Citation Issues Test Paper",
            "description": "JACoW LaTeX manuscript with 5 intentional citation format violations.",
            "file": os.path.join(EXAMPLE_DIR, "latex_jacow_issues.tex"),
            "filename": "MOP004_latex_jacow_issues.tex",
            "content_type": "application/x-tex",
        },
        {
            "code": "MOP005",
            "title": "PASJ 2026 Word 投稿要領・原稿作成の手引き (Official Sample Paper)",
            "description": "Official PASJ 2026 Japanese Word sample manuscript (PASJ_Sample_Paper.docx, 0 errors).",
            "file": os.path.join(EXAMPLE_DIR, "PASJ_Sample_Paper.docx"),
            "filename": "MOP005_PASJ_Sample_Paper.docx",
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
        {
            "code": "MOP006",
            "title": "PASJ Word 和文原稿 書式・句読点規則違反テスト",
            "description": "PASJ Word 和文原稿における英文題名欠落、全角著者カンマ、要旨日文混入、全角句読点違反テスト。",
            "file": os.path.join(EXAMPLE_DIR, "word_pasj_issues.docx"),
            "filename": "MOP006_word_pasj_issues.docx",
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
        {
            "code": "MOP007",
            "title": "PASJ 2026 公式 LaTeX テンプレート原稿 (PASJ_Sample_Paper.tex)",
            "description": "Official PASJ 2026 LaTeX template manuscript (TeXtemplate2026.tex / PASJ_Sample_Paper.tex, 0 issues).",
            "file": os.path.join(EXAMPLE_DIR, "PASJ_Sample_Paper.tex"),
            "filename": "MOP007_PASJ_Sample_Paper.tex",
            "content_type": "application/x-tex",
        },
        {
            "code": "MOP008",
            "title": "PASJ LaTeX 投稿要領 準拠サンプル原稿 (Clean Benchmark)",
            "description": "Standard PASJ Japanese compliant LaTeX manuscript test case (latex_pasj_perfect.tex, 0 issues).",
            "file": os.path.join(EXAMPLE_DIR, "latex_pasj_perfect.tex"),
            "filename": "MOP008_latex_pasj_perfect.tex",
            "content_type": "application/x-tex",
        },
        {
            "code": "MOP009",
            "title": "PASJ LaTeX 和文原稿 引用・句読点・キャプション規則違反テスト",
            "description": "PASJ LaTeX 和文原稿における文書クラス、題目、全角著者区切り、英文要旨日文、図表英文表記、参考文献違反テスト。",
            "file": os.path.join(EXAMPLE_DIR, "latex_pasj_issues.tex"),
            "filename": "MOP009_latex_pasj_issues.tex",
            "content_type": "application/x-tex",
        },
    ]

    created_contribs = []
    for p_info in papers:
        code = p_info["code"]
        contrib = create_contribution(
            event,
            {
                "title": p_info["title"],
                "description": p_info["description"],
                "code": code,
                "duration": timedelta(minutes=20),
            },
        )
        contrib.person_links.append(
            ContributionPersonLink(person=person, is_speaker=True, author_type=AuthorType.primary)
        )
        db.session.flush()

        editable = Editable(contribution=contrib, type=EditableType.paper)
        db.session.add(editable)
        db.session.flush()

        rev = EditingRevision(editable=editable, user=author)
        db.session.add(rev)
        db.session.flush()

        with open(p_info["file"], "rb") as f:
            file_obj = File(filename=p_info["filename"], content_type=p_info["content_type"])
            file_obj.save("default", f)
            db.session.add(file_obj)
            db.session.flush()

            rf = EditingRevisionFile(revision=rev, file=file_obj, file_type=src_ft)
            db.session.add(rf)
            db.session.commit()

        created_contribs.append({
            "id": contrib.id,
            "friendly_id": contrib.friendly_id,
            "code": code,
            "title": p_info["title"],
            "filename": p_info["filename"],
        })

    result = {
        "event_id": event.id,
        "event_title": event.title,
        "contributions": created_contribs,
    }
    print("EVENT_CREATED_JSON:" + json.dumps(result, ensure_ascii=False), flush=True)
