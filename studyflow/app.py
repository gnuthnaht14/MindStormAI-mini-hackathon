from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from studyflow.config import AppSettings  # noqa: E402
from studyflow.models import PDFExtraction, Question, StudyMaterial  # noqa: E402
from studyflow.services import (  # noqa: E402
    AIGenerationError,
    MissingAPIKeyError,
    PDFExtractionError,
    PDFValidationError,
    build_markdown,
    extract_pdf_text,
    generate_study_material,
    validate_pdf,
)


load_dotenv(ROOT / ".env")
SETTINGS = AppSettings.from_env()
DEMO_LESSON_PATH = ROOT / "sample" / "demo_lesson.md"
DEMO_OUTPUT_PATH = ROOT / "sample" / "demo_output.json"
DEMO_PDF_PATH = ROOT / "sample" / "demo.pdf"

QUESTION_TYPE_OPTIONS = {
    "Trắc nghiệm": "multiple_choice",
    "Đúng / Sai": "true_false",
    "Tự luận ngắn": "short_answer",
}
QUESTION_TYPE_LABELS = {
    "multiple_choice": "Trắc nghiệm",
    "true_false": "Đúng / Sai",
    "short_answer": "Tự luận ngắn",
}


st.set_page_config(
    page_title="StudyFlow AI — Biến slide thành tài liệu ôn tập",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --primary: #6f79ff;
            --primary-dark: #5661ee;
            --primary-soft: #eeefff;
            --ink: #151a2b;
            --muted: #687086;
            --line: #e3e6ef;
            --canvas: #f4f5ff;
        }
        html, body, [class*="css"] { font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
        .stApp { background: var(--canvas); color: var(--ink); }
        [data-testid="stHeader"] { background: transparent; }
        /* Keep Streamlit's sidebar controls visible. Hiding the whole toolbar
           also removes the only way to reopen a collapsed sidebar. */
        [data-testid="stToolbar"] { display: flex; }
        [data-testid="stSidebarCollapsedControl"] {
            display: block !important;
            visibility: visible !important;
            z-index: 1000000;
        }
        .block-container { max-width: 1500px; padding: 1.35rem 1.6rem 3rem; }

        [data-testid="stSidebar"] { background: #fff; border-right: 1px solid var(--line); }
        [data-testid="stSidebar"] > div { padding-top: 1.25rem; }
        [data-testid="stSidebar"] .stButton > button { width: 100%; }

        h1, h2, h3 { letter-spacing: -.035em; color: var(--ink); }
        .brand { display:flex; align-items:center; gap:.7rem; margin-bottom:1.5rem; }
        .brand-orb {
            width:40px; height:40px; border-radius:50%; display:grid; place-items:center; color:#fff; font-size:1.15rem;
            background:radial-gradient(circle at 30% 20%, #c78cff 0 10%, #795fff 45%, #31c9ec 100%);
            box-shadow:0 8px 20px rgba(105,91,255,.24);
        }
        .brand strong { font-size:1.2rem; letter-spacing:-.04em; }
        .brand small { display:block; color:#8a91a4; font-size:.66rem; margin-top:.05rem; }
        .side-kicker { color:#8990a2; font-size:.68rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; margin:1.4rem 0 .55rem; }

        .topbar { display:flex; justify-content:space-between; align-items:center; gap:1rem; margin:0 0 1.1rem; }
        .crumb { color:var(--primary); font-size:.9rem; font-weight:700; }
        .crumb span { color:#9da3b2; margin:0 .55rem; }
        .top-badge { display:inline-flex; align-items:center; gap:.4rem; padding:.42rem .75rem; border-radius:999px; background:#fff; border:1px solid var(--line); color:#667085; font-size:.72rem; font-weight:700; }
        .top-badge i { width:7px; height:7px; border-radius:50%; background:#27bf74; }

        .hero-card {
            border-radius:22px; padding:1.65rem 1.8rem; margin-bottom:1rem; color:#fff; overflow:hidden; position:relative;
            background:linear-gradient(120deg, #5c66ee 0%, #7771ff 52%, #9d6dec 100%);
            box-shadow:0 16px 35px rgba(74,80,194,.17);
        }
        .hero-card:after { content:""; position:absolute; width:220px; height:220px; right:-60px; top:-95px; border-radius:50%; border:38px solid rgba(255,255,255,.08); }
        .hero-card .eyebrow { opacity:.78; font-size:.68rem; font-weight:800; letter-spacing:.13em; text-transform:uppercase; }
        .hero-card h1 { color:#fff; margin:.45rem 0 .5rem; font-size:clamp(1.55rem,2.5vw,2.35rem); }
        .hero-card p { max-width:700px; margin:0; opacity:.85; font-size:.9rem; line-height:1.55; }

        [data-testid="stFileUploader"] { padding:1rem; border:1px dashed #bec4ff; border-radius:16px; background:#fafaff; }
        [data-testid="stFileUploaderDropzone"] { background:#fafaff; border:0; }
        .stButton > button, .stDownloadButton > button { border-radius:11px; min-height:2.8rem; font-weight:750; }
        .stButton > button[kind="primary"] { border:0; background:var(--primary); box-shadow:0 8px 18px rgba(111,121,255,.18); }
        .stButton > button[kind="primary"]:hover { background:var(--primary-dark); }

        [data-testid="stTabs"] [data-baseweb="tab-list"] { gap:.25rem; background:#e9e9ff; padding:.35rem .35rem 0; border-radius:16px 16px 0 0; }
        [data-testid="stTabs"] [role="tab"] { border-radius:12px 12px 0 0; padding:.8rem .95rem; font-weight:750; }
        [data-testid="stTabs"] [aria-selected="true"] { background:#fff; color:var(--primary); }
        [data-testid="stTabs"] [data-baseweb="tab-panel"] { background:#fff; border-radius:0 0 18px 18px; padding:1.2rem; border:1px solid #eceef5; border-top:0; }

        .metric-row { display:grid; grid-template-columns:repeat(3,1fr); gap:.65rem; margin:.75rem 0 1rem; }
        .metric-card { border:1px solid var(--line); border-radius:13px; padding:.8rem .9rem; background:#fff; }
        .metric-card strong { display:block; font-size:1.05rem; }
        .metric-card span { color:var(--muted); font-size:.68rem; }
        .empty-state { text-align:center; padding:3rem 1rem; color:var(--muted); }
        .empty-icon { width:58px; height:58px; margin:0 auto 1rem; border-radius:18px; display:grid; place-items:center; font-size:1.55rem; color:var(--primary); background:var(--primary-soft); }
        .empty-state h3 { margin:.2rem 0 .4rem; }
        .empty-state p { max-width:460px; margin:0 auto; font-size:.85rem; line-height:1.5; }
        .key-point { display:flex; gap:.7rem; align-items:flex-start; padding:.7rem .8rem; margin:.45rem 0; border-radius:11px; background:#f7f7ff; }
        .key-point b { width:22px; height:22px; flex:0 0 auto; border-radius:7px; display:grid; place-items:center; background:#e6e7ff; color:var(--primary); font-size:.7rem; }
        .key-point span { font-size:.87rem; line-height:1.45; }
        .question-head { display:flex; align-items:center; justify-content:space-between; gap:1rem; }
        .question-type { display:inline-block; padding:.25rem .55rem; border-radius:999px; background:#efefff; color:var(--primary); font-size:.65rem; font-weight:800; }

        .tutor-panel { border:1px solid #e5e7f0; border-radius:20px; background:#fff; padding:1.2rem; min-height:530px; position:sticky; top:1rem; }
        .tutor-title { color:#9297a5; font-size:.8rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }
        .ai-orb {
            width:132px; height:132px; margin:2rem auto 1.55rem; border-radius:50%;
            background:radial-gradient(circle at 58% 30%, #79e0ff 0 8%, #408fff 22%, transparent 44%), radial-gradient(circle at 35% 67%, #7034ff 0 15%, #1725ad 45%, #4b0eae 67%, #b91af5 86%);
            box-shadow:inset -13px -20px 24px rgba(22,10,116,.38), inset 10px 10px 20px rgba(245,136,255,.38), 0 13px 28px rgba(102,44,236,.2);
        }
        .tutor-panel h3 { text-align:center; margin:.2rem 0 .55rem; }
        .tutor-panel > p { text-align:center; color:var(--muted); font-size:.8rem; line-height:1.5; }
        .pipeline-step { display:flex; gap:.7rem; align-items:center; padding:.65rem 0; border-bottom:1px solid #f0f1f5; font-size:.78rem; color:#6a7183; }
        .step-dot { width:24px; height:24px; border-radius:8px; display:grid; place-items:center; background:#f0f1ff; color:var(--primary); font-size:.7rem; font-weight:800; }
        .step-dot.done { background:#e8f7ef; color:#1f9e61; }
        .coming { margin-top:1rem; padding:.8rem; border-radius:12px; background:#f8f8fc; color:#81879a; font-size:.72rem; text-align:center; }

        @media(max-width:900px) {
            .block-container { padding:.8rem .7rem 2rem; }
            .hero-card { padding:1.3rem; }
            .metric-row { grid-template-columns:1fr; }
            .tutor-panel { position:static; min-height:auto; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    defaults = {
        "uploader_nonce": 0,
        "document_hash": None,
        "extraction": None,
        "material": None,
        "processing_error": None,
        "generation_seconds": None,
        "is_demo": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_document_state(*, reset_uploader: bool = False) -> None:
    for key in ("document_hash", "extraction", "material", "processing_error", "generation_seconds", "is_demo"):
        st.session_state[key] = None if key != "is_demo" else False
    if reset_uploader:
        st.session_state.uploader_nonce += 1


def load_demo() -> None:
    demo_text = DEMO_LESSON_PATH.read_text(encoding="utf-8")
    sections = [section.strip() for section in demo_text.split("\n## ") if section.strip()]
    material = StudyMaterial.model_validate_json(DEMO_OUTPUT_PATH.read_text(encoding="utf-8"))
    st.session_state.document_hash = "demo"
    st.session_state.extraction = PDFExtraction(
        filename="AI20K-Build-Phase-Onboarding-demo.pdf",
        text=demo_text,
        page_count=len(sections),
        character_count=len(demo_text),
        processed_characters=len(demo_text),
        page_texts=sections,
        was_truncated=False,
    )
    st.session_state.material = material
    st.session_state.processing_error = None
    st.session_state.generation_seconds = 0.0
    st.session_state.is_demo = True
    st.session_state.uploader_nonce += 1


def get_configured_api_key() -> str | None:
    if os.getenv("OPENAI_API_KEY"):
        return os.getenv("OPENAI_API_KEY")
    try:
        return st.secrets.get("OPENAI_API_KEY")
    except Exception:
        return None


def render_empty(title: str, message: str, icon: str = "✦") -> None:
    st.markdown(
        f'<div class="empty-state"><div class="empty-icon">{icon}</div><h3>{title}</h3><p>{message}</p></div>',
        unsafe_allow_html=True,
    )


def render_metrics(extraction: PDFExtraction) -> None:
    st.markdown(
        f"""
        <div class="metric-row">
            <div class="metric-card"><strong>{extraction.page_count}</strong><span>TRANG PDF</span></div>
            <div class="metric-card"><strong>{extraction.character_count:,}</strong><span>KÝ TỰ TRÍCH XUẤT</span></div>
            <div class="metric-card"><strong>{extraction.processed_characters:,}</strong><span>KÝ TỰ AI XỬ LÝ</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_question(question: Question, index: int) -> None:
    with st.container(border=True):
        st.markdown(
            f'<div class="question-head"><strong>Câu {index}</strong><span class="question-type">{QUESTION_TYPE_LABELS[question.type]}</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(f"**{question.question}**")
        if question.options:
            st.radio(
                "Chọn câu trả lời",
                question.options,
                index=None,
                key=f"question_{index}_{hash(question.question)}",
                label_visibility="collapsed",
            )
        with st.expander("Xem đáp án và giải thích"):
            st.success(f"Đáp án: {question.answer}")
            st.markdown(question.explanation)


inject_styles()
init_state()

api_key = get_configured_api_key()
selected_model = SETTINGS.openai_model

with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="brand-orb">♙</div><div><strong>studyflow AI</strong><small>SLIDE LEARNING WORKSPACE</small></div></div>',
        unsafe_allow_html=True,
    )
    if st.button("＋ New Study Session", type="primary", use_container_width=True):
        clear_document_state(reset_uploader=True)
        st.rerun()

    st.markdown('<div class="side-kicker">Generate options</div>', unsafe_allow_html=True)
    question_count = st.slider("Số câu hỏi", min_value=5, max_value=10, value=8)
    selected_type_labels = st.multiselect(
        "Dạng câu hỏi",
        list(QUESTION_TYPE_OPTIONS),
        default=["Trắc nghiệm", "Tự luận ngắn"],
    )
    st.caption("MVP dùng một lần gọi AI để tạo summary và quiz cùng lúc.")

    st.divider()
    st.markdown('<div class="side-kicker">Demo backup</div>', unsafe_allow_html=True)
    if st.button("▶ Dùng dữ liệu demo", use_container_width=True):
        load_demo()
        st.rerun()
    st.download_button(
        "↓ Tải PDF demo",
        data=DEMO_PDF_PATH.read_bytes(),
        file_name="studyflow-demo.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
    st.caption("Output mẫu giúp demo giao diện khi API hoặc mạng gặp sự cố.")

st.markdown(
    '<div class="topbar"><div class="crumb">Home <span>›</span> AI Study Session</div><div class="top-badge"><i></i>MVP READY</div></div>',
    unsafe_allow_html=True,
)
st.markdown(
    """
    <section class="hero-card">
        <div class="eyebrow">From slides to active learning</div>
        <h1>Biến slide thành tài liệu ôn tập trong một lần nhấn.</h1>
        <p>Upload PDF có text layer, StudyFlow sẽ đọc nội dung và tạo bản tóm tắt, ý chính cùng bộ câu hỏi có đáp án bằng tiếng Việt.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

main_col, tutor_col = st.columns([3.15, 1], gap="medium")

with main_col:
    with st.container(border=True):
        uploaded_file = st.file_uploader(
            "Upload slide bài giảng",
            type=["pdf"],
            key=f"pdf_upload_{st.session_state.uploader_nonce}",
            help=f"Tối đa {SETTINGS.max_upload_mb} MB, PDF cần có text layer.",
        )

        if uploaded_file is not None:
            file_bytes = uploaded_file.getvalue()
            document_hash = hashlib.sha256(file_bytes).hexdigest()
            if document_hash != st.session_state.document_hash:
                clear_document_state()
                try:
                    with st.spinner("Đang kiểm tra và đọc nội dung PDF…"):
                        validate_pdf(
                            filename=uploaded_file.name,
                            file_bytes=file_bytes,
                            mime_type=uploaded_file.type,
                            max_size_bytes=SETTINGS.max_upload_mb * 1024 * 1024,
                        )
                        extraction = extract_pdf_text(
                            file_bytes,
                            filename=uploaded_file.name,
                            max_characters=SETTINGS.max_input_characters,
                        )
                    st.session_state.document_hash = document_hash
                    st.session_state.extraction = extraction
                except (PDFValidationError, PDFExtractionError) as exc:
                    st.session_state.document_hash = document_hash
                    st.session_state.processing_error = str(exc)

        extraction: PDFExtraction | None = st.session_state.extraction
        if st.session_state.processing_error:
            st.error(st.session_state.processing_error, icon="⚠️")
        elif extraction is not None:
            st.success(f"Đã đọc xong {extraction.filename}", icon="✅")
            render_metrics(extraction)
            if extraction.was_truncated:
                st.warning("Tài liệu dài; MVP chỉ gửi phần nội dung đầu đến AI.")

            selected_question_types = [QUESTION_TYPE_OPTIONS[label] for label in selected_type_labels]
            generate_label = "Tạo lại tài liệu ôn tập" if st.session_state.material else "Tạo tài liệu ôn tập"
            if st.button(
                f"✦ {generate_label}",
                type="primary",
                use_container_width=True,
                disabled=not selected_question_types,
            ):
                started_at = time.perf_counter()
                try:
                    with st.spinner("AI đang tóm tắt và tạo câu hỏi ôn tập…"):
                        st.session_state.material = generate_study_material(
                            extraction.text,
                            question_count=question_count,
                            question_types=selected_question_types,
                            api_key=api_key,
                            model=selected_model.strip() or SETTINGS.openai_model,
                            base_url=SETTINGS.openai_base_url,
                        )
                    st.session_state.generation_seconds = time.perf_counter() - started_at
                    st.session_state.is_demo = False
                    st.rerun()
                except (MissingAPIKeyError, AIGenerationError, ValueError) as exc:
                    st.error(str(exc), icon="⚠️")

    material: StudyMaterial | None = st.session_state.material
    original_tab, notes_tab, summary_tab, flashcards_tab, quiz_tab = st.tabs(
        ["Original Content", "AI Notes", "AI Summary", "AI Flashcards", "AI Quiz"]
    )

    with original_tab:
        if extraction is None:
            render_empty("Chưa có tài liệu", "Upload một PDF để xem nội dung được trích xuất theo từng trang.", "▤")
        else:
            st.subheader(extraction.filename)
            st.caption("Preview text layer được PyMuPDF trích xuất")
            for page_index, page_text in enumerate(extraction.page_texts, start=1):
                with st.expander(f"Trang {page_index}", expanded=page_index == 1):
                    st.text(page_text or "Trang này không có text layer.")

    with notes_tab:
        render_empty("AI Notes sẽ có trong bước tiếp theo", "MVP hiện tập trung vào happy path PDF → Summary → Quiz.", "✎")

    with summary_tab:
        if material is None:
            render_empty("Chưa có bản tóm tắt", "Đọc PDF và nhấn “Tạo tài liệu ôn tập” để bắt đầu.")
        else:
            demo_label = " · output demo" if st.session_state.is_demo else ""
            elapsed = st.session_state.generation_seconds
            timing = f" · {elapsed:.1f}s" if elapsed is not None else ""
            st.caption(f"{len(material.key_points)} ý chính{timing}{demo_label}")
            st.header(material.title)
            st.markdown(material.summary)
            st.subheader("Ý chính cần nhớ")
            for index, key_point in enumerate(material.key_points, start=1):
                st.markdown(
                    f'<div class="key-point"><b>{index}</b><span>{key_point}</span></div>',
                    unsafe_allow_html=True,
                )

            markdown_export = build_markdown(material, extraction)
            download_col, copy_col = st.columns(2)
            with download_col:
                st.download_button(
                    "↓ Tải kết quả Markdown",
                    data=markdown_export,
                    file_name="studyflow-study-material.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with copy_col:
                with st.popover("⧉ Copy nội dung", use_container_width=True):
                    st.caption("Dùng nút copy ở góc khối nội dung bên dưới.")
                    st.code(markdown_export, language="markdown")

    with flashcards_tab:
        render_empty("AI Flashcards sắp có", "Schema flashcard và spaced repetition nằm ngoài phạm vi MVP đầu tiên.", "▱")

    with quiz_tab:
        if material is None:
            render_empty("Chưa có câu hỏi ôn tập", "AI sẽ tạo 5–10 câu hỏi có đáp án và giải thích từ PDF của bạn.", "☷")
        else:
            st.subheader(f"Bộ câu hỏi ôn tập · {len(material.questions)} câu")
            st.caption("Thử trả lời trước, sau đó mở phần đáp án để tự kiểm tra.")
            for question_index, question in enumerate(material.questions, start=1):
                render_question(question, question_index)

with tutor_col:
    extraction_ready = extraction is not None
    material_ready = st.session_state.material is not None
    st.markdown(
        f"""
        <aside class="tutor-panel">
            <div class="tutor-title">AI Tutor</div>
            <div class="ai-orb"></div>
            <h3>Study pipeline</h3>
            <p>StudyFlow biến nội dung thụ động thành một gói ôn tập có cấu trúc.</p>
            <div class="pipeline-step"><span class="step-dot {'done' if extraction_ready else ''}">1</span>Upload PDF bài giảng</div>
            <div class="pipeline-step"><span class="step-dot {'done' if extraction_ready else ''}">2</span>Extract text theo trang</div>
            <div class="pipeline-step"><span class="step-dot {'done' if material_ready else ''}">3</span>AI Summary + Quiz</div>
            <div class="pipeline-step"><span class="step-dot">4</span>Ôn tập và tải kết quả</div>
            <div class="coming">Hỏi đáp trực tiếp trên tài liệu sẽ được bổ sung sau MVP.</div>
        </aside>
        """,
        unsafe_allow_html=True,
    )
