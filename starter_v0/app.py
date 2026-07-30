from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title="StudyFlow AI — Slide Learning Workspace",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.html(
    """
    <style>
        :root {
            --primary: #6f79ff;
            --primary-2: #8b62ff;
            --primary-soft: #ebeaff;
            --canvas: #f3f4ff;
            --surface: #ffffff;
            --ink: #141a2a;
            --muted: #667085;
            --line: #e3e6ef;
            --success: #22c46b;
        }

        * { box-sizing: border-box; }
        html, body, [class*="css"] {
            font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        body { overflow: hidden; }
        .stApp { background: var(--canvas); }
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stSidebar"],
        [data-testid="stStatusWidget"] { display: none !important; }
        .block-container { max-width: none !important; padding: 0 !important; }
        [data-testid="stMainBlockContainer"] { padding: 0 !important; }

        button { font: inherit; }
        .study-app {
            position: fixed;
            inset: 0;
            z-index: 999;
            display: grid;
            grid-template-columns: 300px minmax(620px, 1fr) 390px;
            grid-template-rows: 72px 64px minmax(0, 1fr);
            background: var(--canvas);
            color: var(--ink);
            overflow: hidden;
        }

        /* Sidebar */
        .sidebar {
            grid-row: 1 / 4;
            background: #fff;
            border-right: 1px solid var(--line);
            padding: 17px 18px 16px;
            display: flex;
            flex-direction: column;
            min-height: 0;
        }
        .brand-row {
            height: 42px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 34px;
        }
        .brand { display: flex; align-items: center; gap: 9px; }
        .brand-orb {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: grid;
            place-items: center;
            color: white;
            font-size: 21px;
            background: radial-gradient(circle at 28% 20%, #bf8cff 0 12%, #795fff 42%, #30caef 100%);
            box-shadow: 0 6px 18px rgba(107, 102, 255, .22);
        }
        .brand-name { font-size: 23px; line-height: 1; font-weight: 800; letter-spacing: -.7px; }
        .brand-name sup { margin-left: 3px; font-size: 10px; font-weight: 700; }
        .collapse-btn {
            width: 30px;
            height: 30px;
            display: grid;
            place-items: center;
            border-radius: 5px;
            color: var(--primary);
            border: 2px solid var(--primary);
            background: #fff;
            font-size: 16px;
        }
        .new-session {
            border: 0;
            min-height: 58px;
            border-radius: 11px;
            background: var(--primary);
            color: white;
            font-size: 17px;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 13px;
            box-shadow: 0 8px 20px rgba(111, 121, 255, .18);
            cursor: default;
        }
        .new-session .plus { font-size: 29px; font-weight: 300; margin-top: -2px; }
        .nav-section { margin-top: 58px; }
        .section-title {
            font-size: 14px;
            font-weight: 700;
            color: #697084;
            margin-bottom: 13px;
        }
        .nav-item {
            display: flex;
            align-items: center;
            gap: 13px;
            height: 44px;
            padding: 0 4px;
            font-size: 16px;
            color: #111827;
        }
        .nav-icon {
            width: 20px;
            color: var(--primary);
            font-size: 20px;
            text-align: center;
        }
        .recent { margin-top: 40px; }
        .recent-title { display: flex; align-items: center; justify-content: space-between; }
        .recent-item {
            display: flex;
            align-items: center;
            gap: 12px;
            height: 46px;
            min-width: 0;
            font-size: 16px;
        }
        .green-dot { width: 12px; height: 12px; flex: 0 0 auto; border-radius: 50%; background: var(--success); }
        .ellipsis { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
        .sidebar-bottom { margin-top: auto; }
        .upgrade {
            padding: 14px 0 16px;
            border-top: 1px solid var(--line);
        }
        .upgrade-title { display: flex; gap: 10px; align-items: center; font-size: 15px; font-weight: 750; margin-bottom: 14px; }
        .mini-orb {
            width: 25px; height: 25px; border-radius: 50%; display: grid; place-items: center;
            color: white; font-size: 12px;
            background: linear-gradient(145deg, #a469ff, #4cc9ef);
        }
        .upgrade-btn {
            height: 44px;
            width: 100%;
            border: 0;
            border-radius: 10px;
            color: white;
            background: var(--primary);
            font-size: 14px;
            font-weight: 700;
        }
        .profile { display: flex; align-items: center; gap: 14px; padding-top: 10px; font-size: 15px; font-weight: 700; }
        .avatar { width: 42px; height: 42px; border-radius: 50%; background: #e7eaff; display: grid; place-items: center; font-size: 17px; font-weight: 500; }

        /* Top bar */
        .topbar {
            grid-column: 2 / 4;
            grid-row: 1;
            height: 72px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 26px;
        }
        .breadcrumb { min-width: 0; display: flex; align-items: center; gap: 20px; }
        .home { color: var(--primary); font-size: 21px; font-weight: 500; }
        .chevron { color: #a3aabd; font-size: 26px; font-weight: 300; }
        .file-name {
            max-width: 430px;
            color: #101426;
            font-size: 20px;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            border-bottom: 1px dashed var(--primary);
            padding-bottom: 2px;
        }
        .edit { color: var(--primary); font-size: 23px; transform: rotate(-10deg); }
        .top-actions { display: flex; align-items: center; gap: 20px; color: var(--primary); }
        .focus-label { font-size: 16px; font-weight: 800; color: #111; }
        .toggle { width: 65px; height: 38px; border-radius: 999px; padding: 4px; background: #dbe0ff; }
        .toggle-knob { width: 30px; height: 30px; border-radius: 50%; background: var(--primary); box-shadow: 0 3px 8px rgba(75, 87, 235, .28); }
        .action-icon { font-size: 25px; line-height: 1; }

        /* Tabs */
        .tabs {
            grid-column: 2;
            grid-row: 2;
            display: flex;
            align-items: end;
            padding: 0 0 0 24px;
            min-width: 0;
            overflow: hidden;
        }
        .tab {
            height: 56px;
            flex: 0 0 auto;
            padding: 0 19px;
            border: 0;
            border-radius: 24px 24px 0 0;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #e9e8ff;
            color: #161b2a;
            font-size: 18px;
            font-weight: 650;
            white-space: nowrap;
        }
        .tab + .tab { margin-left: -1px; }
        .tab.active { background: #fff; font-weight: 700; }
        .tab .ai { color: var(--primary); margin-right: 5px; font-weight: 750; }
        .count-ring {
            width: 48px; height: 48px; margin: 0 10px 4px 12px; border-radius: 50%;
            border: 5px solid #daddE6; border-top-color: var(--primary);
            background: #f6f6fa; display: grid; place-items: center; font-size: 14px; font-weight: 700;
        }
        .tutor-title {
            grid-column: 3;
            grid-row: 2;
            display: flex;
            align-items: center;
            padding: 9px 0 0 24px;
            color: #8a8e9a;
            font-size: 21px;
            font-weight: 750;
        }

        /* Main viewer */
        .main-shell {
            grid-column: 2;
            grid-row: 3;
            margin: 0 10px 16px 24px;
            padding: 12px 18px 18px;
            background: #fff;
            border-radius: 0 22px 22px 22px;
            min-width: 0;
            min-height: 0;
            display: flex;
            flex-direction: column;
            box-shadow: 0 2px 5px rgba(62, 67, 113, .02);
        }
        .file-strip {
            height: 56px;
            padding: 9px 12px;
            display: flex;
            align-items: center;
            gap: 8px;
            border-radius: 12px;
            background: #f7f8fd;
            flex: 0 0 auto;
        }
        .add-file {
            width: 40px;
            height: 40px;
            border-radius: 11px;
            border: 1.5px solid var(--primary);
            background: #fff;
            color: var(--primary);
            font-size: 29px;
            line-height: 1;
        }
        .file-pill {
            width: min(470px, 62%);
            height: 40px;
            padding: 0 18px;
            border-radius: 10px;
            background: var(--primary);
            color: white;
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 0;
            font-size: 14px;
            font-weight: 700;
        }
        .doc-icon { width: 25px; height: 28px; border: 2px solid #fff; border-radius: 6px; display: grid; place-items: center; font-size: 12px; }
        .viewer {
            position: relative;
            flex: 1 1 auto;
            min-height: 0;
            margin: 18px 22px 0;
            border: 1px solid #dfe2e8;
            background: #fafafa;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .toolbar {
            height: 52px;
            padding: 0 14px;
            flex: 0 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            border-bottom: 1px solid #e5e7eb;
            background: #fff;
        }
        .toolbar-group { display: flex; align-items: center; gap: 14px; color: #111; }
        .tool { font-size: 20px; color: #111; line-height: 1; white-space: nowrap; }
        .page-field { width: 52px; height: 34px; display: grid; place-items: center; border: 1px solid #cfd3da; border-radius: 3px; font-size: 16px; }
        .toolbar-text { font-size: 16px; }
        .slide-stage {
            flex: 1 1 auto;
            min-height: 0;
            padding: 13px 26px 16px;
            overflow: hidden;
            background: #f5f5f5;
        }
        .slide-page {
            width: min(100%, 710px);
            min-height: 430px;
            aspect-ratio: 16 / 10;
            margin: 0 auto;
            position: relative;
            padding: 100px 55px 38px;
            background: white;
            box-shadow: 6px 8px 14px rgba(24, 30, 56, .14);
            overflow: hidden;
        }
        .orange-line { position: absolute; left: 0; top: 0; width: 100%; height: 14px; background: #f07300; }
        .slide-kicker { text-align: center; color: #f07300; font-size: 12px; font-weight: 800; letter-spacing: .03em; }
        .slide-page h1 { margin: 15px 0 6px; text-align: center; font-size: 31px; letter-spacing: -.5px; }
        .slide-subtitle { text-align: center; color: #5b6270; font-size: 13px; }
        .invite-box {
            width: 88%;
            margin: 30px auto 26px;
            padding: 10px 14px;
            border: 1.5px solid #f07300;
            background: #fff0e3;
            font-size: 10px;
            line-height: 1.6;
        }
        .invite-box b { display: block; font-size: 10px; }
        .steps-title { width: 86%; margin: 0 auto 10px; font-size: 12px; font-weight: 800; }
        .steps { width: 86%; margin: 0 auto; border-collapse: collapse; font-size: 10px; }
        .steps td { padding: 5px 4px; border-bottom: 1px solid #dce0e6; }
        .steps td:first-child { width: 28px; color: #f07300; font-weight: 800; }
        .scroll-track { position: absolute; right: 7px; top: 68px; bottom: 12px; width: 7px; border-radius: 99px; background: #eef0f7; }
        .scroll-thumb { width: 7px; height: 28px; border-radius: 99px; background: #b2b9ff; margin-top: 18px; }

        /* Tutor */
        .tutor-shell {
            grid-column: 3;
            grid-row: 3;
            margin: 0 20px 16px 10px;
            border-radius: 22px;
            background: #fff;
            min-height: 0;
            overflow: hidden;
            position: relative;
        }
        .tutor-inner {
            height: 100%;
            padding: 28px 24px 26px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .quick-actions { width: 100%; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .quick-card {
            height: 76px;
            padding: 12px;
            border: 1px solid #e0e3ea;
            border-radius: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 0;
        }
        .quick-icon { width: 42px; height: 42px; border-radius: 11px; background: #f0f1ff; color: var(--primary); display: grid; place-items: center; font-size: 22px; }
        .quick-copy { min-width: 0; }
        .popular { display: inline-block; padding: 3px 8px; border-radius: 999px; color: var(--primary); background: #f1f0ff; font-size: 10px; font-weight: 800; }
        .quick-label { margin-top: 5px; color: #626879; font-size: 12px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
        .ai-orb {
            width: 168px;
            height: 168px;
            margin: 52px 0 36px;
            border-radius: 50%;
            background:
                radial-gradient(circle at 55% 34%, rgba(121, 224, 255, .98) 0 9%, rgba(64, 143, 255, .84) 22%, transparent 45%),
                radial-gradient(circle at 35% 67%, #6f34ff 0 14%, #1520ae 44%, #4a0eac 65%, #b71af5 84%, #5a3aff 100%);
            box-shadow: inset -16px -24px 30px rgba(23, 10, 116, .40), inset 12px 12px 24px rgba(245, 136, 255, .42), 0 15px 34px rgba(102, 44, 236, .22);
        }
        .tutor-copy { max-width: 315px; text-align: center; }
        .tutor-copy h2 { margin: 0 0 20px; font-size: 23px; line-height: 1.35; letter-spacing: -.4px; }
        .tutor-copy p { margin: 0; color: #202536; font-size: 15px; line-height: 1.55; }
        .prompt-box {
            width: 100%;
            min-height: 48px;
            margin-top: auto;
            border: 1px solid #d8dce6;
            border-radius: 13px;
            padding: 13px 14px;
            color: #465067;
            font-size: 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .send-dot { width: 29px; height: 29px; border-radius: 50%; background: #eceeff; color: var(--primary); display: grid; place-items: center; }
        .tutor-scroll { position: absolute; right: 3px; top: 0; bottom: 0; width: 8px; border-radius: 99px; background: #aab1ff; }

        @media (max-width: 1380px) {
            .study-app { grid-template-columns: 250px minmax(560px, 1fr) 330px; }
            .sidebar { padding-left: 14px; padding-right: 14px; }
            .tab { padding: 0 13px; font-size: 15px; }
            .file-name { max-width: 320px; }
            .ai-orb { width: 145px; height: 145px; margin-top: 40px; }
            .slide-page { padding-top: 75px; }
        }

        @media (max-width: 1100px) {
            .study-app { grid-template-columns: 76px minmax(560px, 1fr) 315px; }
            .sidebar { padding: 16px 10px; align-items: center; }
            .brand-name, .collapse-btn, .new-session span:last-child, .section-title,
            .nav-item span:last-child, .recent, .upgrade-title span:last-child, .upgrade-btn,
            .profile span:last-child { display: none; }
            .brand-row { justify-content: center; }
            .new-session { width: 48px; min-height: 48px; }
            .nav-section { margin-top: 38px; }
            .nav-item { justify-content: center; }
            .sidebar-bottom { width: 100%; }
            .upgrade { display: flex; justify-content: center; }
            .profile { justify-content: center; }
            .tabs { padding-left: 14px; }
            .main-shell { margin-left: 14px; }
            .focus-label { display: none; }
        }
    </style>

    <main class="study-app">
        <aside class="sidebar">
            <div class="brand-row">
                <div class="brand">
                    <div class="brand-orb">♙</div>
                    <div class="brand-name">studyflow<sup>AI</sup></div>
                </div>
                <button class="collapse-btn" aria-label="Collapse sidebar">◁</button>
            </div>

            <button class="new-session"><span class="plus">＋</span><span>New Study Session</span></button>

            <section class="nav-section">
                <div class="section-title">Library</div>
                <div class="nav-item"><span class="nav-icon">▥</span><span>Study sessions</span></div>
                <div class="nav-item"><span class="nav-icon">♧</span><span>Shared with me</span></div>
                <div class="nav-item"><span class="nav-icon">□</span><span>Folders</span></div>
            </section>

            <section class="recent">
                <div class="section-title recent-title"><span>Recent</span><span>⌄</span></div>
                <div class="recent-item"><span class="green-dot"></span><span class="ellipsis">AI20K-Build-Phase-Onboarding...</span></div>
            </section>

            <div class="sidebar-bottom">
                <div class="upgrade">
                    <div class="upgrade-title"><span class="mini-orb">♙</span><span>Upgrade for more features</span></div>
                    <button class="upgrade-btn">Upgrade</button>
                </div>
                <div class="profile"><span class="avatar">TT</span><span>Trọng Thành Nhữ</span></div>
            </div>
        </aside>

        <header class="topbar">
            <div class="breadcrumb">
                <span class="home">Home</span>
                <span class="chevron">›</span>
                <span class="file-name">AI20K-Build-Phase-Onboarding...</span>
                <span class="edit">✎</span>
            </div>
            <div class="top-actions">
                <span class="focus-label">Focused Reading</span>
                <span class="toggle"><span class="toggle-knob"></span></span>
                <span class="action-icon">⇧</span>
                <span class="action-icon">♧</span>
            </div>
        </header>

        <nav class="tabs" aria-label="Study content tabs">
            <button class="tab active">Original Content</button>
            <button class="tab"><span class="ai">AI</span> Notes</button>
            <button class="tab"><span class="ai">AI</span> Summary</button>
            <button class="tab"><span class="ai">AI</span> Flashcards</button>
            <button class="tab"><span class="ai">AI</span> Quizzes</button>
            <span class="count-ring">2</span>
        </nav>
        <div class="tutor-title">AI Tutor</div>

        <section class="main-shell">
            <div class="file-strip">
                <button class="add-file" aria-label="Add file">＋</button>
                <div class="file-pill"><span class="doc-icon">▤</span><span class="ellipsis">AI20K-Build-Phase-Onboarding-Hướng-dẫn.pdf</span></div>
            </div>

            <div class="viewer">
                <div class="toolbar">
                    <div class="toolbar-group">
                        <span class="tool">⌕</span><span class="tool">⌃</span>
                        <span class="page-field">1</span><span class="toolbar-text">16</span><span class="tool">⌄</span>
                    </div>
                    <div class="toolbar-group"><span class="tool">⊖</span><span class="toolbar-text">80% ▾</span><span class="tool">⊕</span></div>
                    <div class="toolbar-group"><span class="tool">↔</span><span class="tool">⇩</span><span class="tool">▧</span><span class="tool">⋮</span></div>
                </div>
                <div class="slide-stage">
                    <article class="slide-page">
                        <div class="orange-line"></div>
                        <div class="slide-kicker">AI20K · BUILD PHASE · COHORT 3</div>
                        <h1>HƯỚNG DẪN ONBOARDING</h1>
                        <div class="slide-subtitle">Dành cho học viên — từ lời mời tham gia đến khi sẵn sàng build cùng đội</div>
                        <div class="invite-box"><b>Link mời tham gia nền tảng:</b>https://phoenix.note.transformerlabs.ai/invite/AI20K-build-phase</div>
                        <div class="steps-title">Lộ trình 7 bước</div>
                        <table class="steps">
                            <tr><td>1</td><td>Truy cập nền tảng qua link mời — đăng nhập bằng GitHub</td></tr>
                            <tr><td>2</td><td>Tham gia Discord server của chương trình</td></tr>
                            <tr><td>3</td><td>Chấp nhận lời mời vào GitHub Organization</td></tr>
                            <tr><td>4</td><td>Hoàn thiện hồ sơ đội và kỹ năng</td></tr>
                        </table>
                    </article>
                </div>
                <div class="scroll-track"><div class="scroll-thumb"></div></div>
            </div>
        </section>

        <aside class="tutor-shell">
            <div class="tutor-inner">
                <div class="quick-actions">
                    <div class="quick-card">
                        <div class="quick-icon">▱</div>
                        <div class="quick-copy"><span class="popular">Popular</span><div class="quick-label">Study with AI</div></div>
                    </div>
                    <div class="quick-card">
                        <div class="quick-icon">☷</div>
                        <div class="quick-copy"><span class="popular">Popular</span><div class="quick-label">Test yourself</div></div>
                    </div>
                </div>

                <div class="ai-orb" aria-hidden="true"></div>
                <div class="tutor-copy">
                    <h2>Have a question about your import?</h2>
                    <p>You can ask questions about your imported content, and your answers will appear here.</p>
                </div>
                <div class="prompt-box"><span>Write a paragraph...</span><span class="send-dot">↑</span></div>
            </div>
            <div class="tutor-scroll"></div>
        </aside>
    </main>
    """
)
