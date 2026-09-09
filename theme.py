"""
theme.py — dashboard chrome (top bar, sidebar nav, card styling, logo) with a
light/dark theme system controlled entirely by Python-side state, so a single
toggle re-skins the whole app (including the top-bar clock, which lives in
its own iframe and gets the palette passed in explicitly).
"""

import streamlit as st

try:
    import streamlit.components.v1 as components
except ImportError:
    components = None

PAGES = ["Home", "Upload & Send", "Manage Entities", "Send Log"]

PALETTES = {
    "dark": {
        "bg_app": "#0a0f1a",
        "bg_panel": "#0d1526",
        "bg_card": "#111c2e",
        "bg_input": "#17233a",
        "bg_hover": "#182742",
        "border": "#22314d",
        "text_primary": "#e9eef6",
        "text_secondary": "#8ea0bd",
        "accent": "#3fc4f2",
        "accent_strong": "#22d3aa",
        "accent_strong_text": "#04241c",
        "shadow": "0 6px 20px rgba(0,0,0,0.35)",
        "topbar_amber": "#f3c34e",
    },
    "light": {
        "bg_app": "#f2f5fa",
        "bg_panel": "#ffffff",
        "bg_card": "#ffffff",
        "bg_input": "#f1f4f9",
        "bg_hover": "#eaf1fb",
        "border": "#dfe6f0",
        "text_primary": "#101a2c",
        "text_secondary": "#5a6b85",
        "accent": "#0284c7",
        "accent_strong": "#0f9d78",
        "accent_strong_text": "#ffffff",
        "shadow": "0 6px 20px rgba(30,45,80,0.08)",
        "topbar_amber": "#b8790a",
    },
}


def get_mode() -> str:
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = True
    return "dark" if st.session_state.dark_mode else "light"


def logo_svg(size: int = 34, grad_id: str = "ppLogoGrad") -> str:
    """A small rounded badge with a stylised bolt — used in the sidebar and
    top bar instead of a cramped text-only box."""
    svg = f"""
    <svg width="{size}" height="{size}" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0;">
      <defs>
        <linearGradient id="{grad_id}" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#3fc4f2"/>
          <stop offset="100%" stop-color="#22d3aa"/>
        </linearGradient>
      </defs>
      <rect width="40" height="40" rx="11" fill="url(#{grad_id})"/>
      <path d="M22 6 L11 23 H18 L17 34 L29 16 H21 L23 6 Z" fill="white" opacity="0.95"/>
    </svg>
    """
    # IMPORTANT: strip leading/trailing whitespace. When this gets spliced
    # into another markdown-rendered HTML string, a stray blank line here
    # terminates the outer HTML block early and everything after it falls
    # back to being rendered as a plain (indented -> code-block) paragraph.
    return svg.strip()


def build_css(p: dict) -> str:
    return f"""
    <style>
    :root {{
        --bg-app: {p['bg_app']};
        --bg-panel: {p['bg_panel']};
        --bg-card: {p['bg_card']};
        --bg-input: {p['bg_input']};
        --bg-hover: {p['bg_hover']};
        --border: {p['border']};
        --text-primary: {p['text_primary']};
        --text-secondary: {p['text_secondary']};
        --accent: {p['accent']};
        --accent-strong: {p['accent_strong']};
        --accent-strong-text: {p['accent_strong_text']};
        --shadow: {p['shadow']};
    }}

    #MainMenu, footer {{ visibility: hidden; height: 0; }}
    header[data-testid="stHeader"] {{ background: transparent; }}
    .stApp {{ background-color: var(--bg-app); }}
    .block-container {{ padding-top: 0.6rem; max-width: 1600px; margin: 0 auto; }}

    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
    html, body, p, div, span, li, a, label,
    .stMarkdown, .stCaption, .stTextInput input, .stTextArea textarea,
    button, input, textarea, select {{
        font-family: 'Manrope', 'Segoe UI', sans-serif;
    }}
    h1, h2, h3, h4, h5, h6 {{ color: var(--text-primary); font-family: 'Manrope', sans-serif; }}
    /* Streamlit's own icons (sidebar collapse arrow, file-uploader icon,
       password show/hide eye) render as ligature text glyphs from this font
       — the broad rule above must never override it, or you get literal
       words like "visibility_off" instead of an icon. */
    [data-testid="stIconMaterial"] {{
        font-family: 'Material Symbols Rounded' !important;
    }}

    /* ---- sub bar / breadcrumb ---- */
    .pp-subbar-wrap {{ padding: 10px 4px 16px 4px; }}
    .pp-welcome {{ color: var(--accent); font-weight:700; font-size:1.02rem; }}
    .pp-breadcrumb-sep {{ color: var(--text-secondary); padding-top: 6px; text-align:center; }}
    div[data-testid="stAppViewContainer"] .pp-breadcrumb-row .stButton>button {{
        background: transparent; border: none; color: var(--text-secondary);
        font-weight: 600; padding: 4px 6px; text-decoration: underline;
        text-underline-offset: 3px; width: auto; white-space: nowrap;
    }}
    div[data-testid="stAppViewContainer"] .pp-breadcrumb-row .stButton>button:hover {{
        color: var(--accent);
    }}

    /* ---- sidebar ---- */
    [data-testid="stSidebar"] {{ background-color: var(--bg-panel); border-right: 1px solid var(--border); }}
    [data-testid="stSidebar"] .pp-brand {{
        display:flex; align-items:center; gap:10px; padding: 10px 6px 26px 6px;
    }}
    .pp-brand-title {{ font-weight:800; font-size:1.08rem; color: var(--text-primary); letter-spacing:0.3px; display:block; }}
    .pp-brand-sub {{ font-size:0.66rem; color: var(--text-secondary); text-transform:uppercase; letter-spacing:1.2px; display:block; }}

    [data-testid="stSidebar"] .stButton>button {{
        width: 100%; text-align:left; background: transparent; color: var(--text-primary);
        border: none; padding: 10px 12px; font-weight:600; border-radius:8px; transition: background 0.15s ease;
    }}
    [data-testid="stSidebar"] .stButton>button:hover {{ background: var(--bg-hover); color: var(--accent); }}
    [data-testid="stSidebar"] .nav-active button {{
        background: var(--bg-hover) !important; color: var(--accent) !important;
        border-left: 3px solid var(--accent) !important;
    }}
    [data-testid="stSidebar"] .pp-sidebar-divider {{
        border-top: 1px solid var(--border); margin: 18px 0;
    }}

    /* ---- card ---- */
    .pp-card {{
        background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
        padding: 4px 22px 22px 22px; margin-bottom: 20px; box-shadow: var(--shadow);
    }}
    .pp-card-header {{
        display:flex; align-items:center; gap:8px; color: var(--text-primary);
        font-weight:700; font-size:1.05rem; padding: 16px 0; border-bottom: 1px solid var(--border);
        margin-bottom: 18px;
    }}
    .pp-card-header .info {{ color: var(--accent); }}

    /* ---- tabs ---- */
    [data-testid="stTabs"] button[role="tab"] {{
        background: var(--bg-input); border: 1px solid var(--border); border-bottom:none;
        color: var(--text-secondary); border-radius: 8px 8px 0 0; padding: 10px 24px; font-weight:600;
    }}
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
        background: var(--bg-card); color: var(--text-primary); border-color: var(--accent);
    }}

    /* ---- inputs ---- */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {{
        background: var(--bg-input) !important; color: var(--text-primary) !important;
        border-color: var(--border) !important; border-radius: 8px !important;
    }}
    label, .stMarkdown, .stCaption, p {{ color: var(--text-primary); }}
    .stCaption, [data-testid="stCaptionContainer"] {{ color: var(--text-secondary) !important; }}

    /* ---- buttons ---- */
    div[data-testid="stAppViewContainer"] .stButton>button[kind="primary"],
    div[data-testid="stAppViewContainer"] [data-testid^="stBaseButton-primary"],
    div[data-testid="stAppViewContainer"] .stFormSubmitButton>button {{
        background: var(--accent-strong); color: var(--accent-strong-text); border: none;
        font-weight:700; border-radius: 8px;
    }}
    div[data-testid="stAppViewContainer"] .stButton>button[kind="primary"]:hover,
    div[data-testid="stAppViewContainer"] [data-testid^="stBaseButton-primary"]:hover,
    div[data-testid="stAppViewContainer"] .stFormSubmitButton>button:hover {{
        filter: brightness(1.08);
    }}
    div[data-testid="stAppViewContainer"] .stButton>button[kind="secondary"],
    div[data-testid="stAppViewContainer"] [data-testid^="stBaseButton-secondary"] {{
        background: var(--bg-input); color: var(--text-primary); border: 1px solid var(--border);
        border-radius: 8px;
    }}
    [data-testid="stDownloadButton"] button {{
        background: var(--bg-input); color: var(--text-primary); border: 1px solid var(--border);
        border-radius: 8px;
    }}

    /* ---- file uploader (was hardcoded dark regardless of theme) ---- */
    [data-testid="stFileUploaderDropzone"] {{
        background: var(--bg-input) !important; border: 1px dashed var(--border) !important;
        border-radius: 8px !important; width: 100%;
    }}
    [data-testid="stFileUploaderDropzoneInstructions"],
    [data-testid="stFileUploaderDropzoneInstructions"] span,
    [data-testid="stFileUploaderDropzoneInstructions"] small {{
        color: var(--text-primary) !important;
    }}
    [data-testid="stFileUploaderFile"] {{
        background: var(--bg-card) !important; border: 1px solid var(--border) !important;
        border-radius: 8px !important;
    }}

    /* ---- field chips (replace st.metric for long, non-truncated values) ---- */
    .pp-field-chip {{
        background: var(--bg-input); border: 1px solid var(--border); border-radius: 8px;
        padding: 10px 14px; height: 100%;
    }}
    .pp-field-chip .label {{ color: var(--text-secondary); font-size:0.78rem; text-transform:uppercase;
                              letter-spacing:0.6px; margin-bottom:4px; }}
    .pp-field-chip .value {{ color: var(--text-primary); font-size:1.15rem; font-weight:700;
                              word-break: break-word; line-height:1.3; }}

    /* ---- alerts / expanders / dataframe: keep consistent with the palette ---- */
    [data-testid="stExpander"] {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; }}
    [data-testid="stDataFrame"] {{ border: 1px solid var(--border); border-radius: 8px; overflow:hidden; }}
    .stAlert {{ border-radius: 8px; }}

    /* ---- password inputs (this Streamlit version doesn't use BaseWeb
       attributes — it's stTextInputRootElement / stTextInputField /
       stTextInputIcon; targeting the wrong ones silently does nothing) ---- */
    [data-testid="stTextInputRootElement"] {{
        background: var(--bg-input) !important; border: 1px solid var(--border) !important;
        border-radius: 8px !important;
    }}
    [data-testid="stTextInputField"] {{
        background: transparent !important; color: var(--text-primary) !important;
        -webkit-text-fill-color: var(--text-primary) !important;
    }}
    [data-testid="stTextInputIcon"] {{ background: transparent !important; color: var(--text-secondary) !important; }}

    /* ---- home page ---- */
    .pp-hero {{ padding: 6px 0 18px 0; }}
    .pp-hero h1 {{ font-size: 1.7rem; margin-bottom: 4px; }}
    .pp-hero p {{ color: var(--text-secondary); font-size: 1rem; max-width: 800px; }}
    .pp-doc-step {{
        display:flex; gap:14px; padding: 14px 0; border-bottom: 1px solid var(--border);
    }}
    .pp-doc-step:last-child {{ border-bottom: none; }}
    .pp-doc-step .num {{
        flex-shrink:0; width:30px; height:30px; border-radius:50%; background: var(--bg-input);
        border:1px solid var(--border); color: var(--accent); font-weight:800;
        display:flex; align-items:center; justify-content:center; font-size:0.9rem;
    }}
    .pp-doc-step .title {{ font-weight:700; color: var(--text-primary); margin-bottom:2px; }}
    .pp-doc-step .desc {{ color: var(--text-secondary); font-size:0.92rem; line-height:1.5; }}

    .pp-mandatory {{ color: var(--accent); font-size:0.85rem; }}

    /* ---- plain HTML data table (used instead of st.dataframe, which is
       canvas-rendered and stays locked to config.toml's fixed dark theme
       regardless of our light/dark toggle) ---- */
    .pp-table-wrap {{
        max-height: 440px; overflow: auto; border: 1px solid var(--border); border-radius: 8px;
    }}
    .pp-table {{ width: 100%; border-collapse: collapse; font-size: 0.86rem; }}
    .pp-table th {{
        position: sticky; top: 0; background: var(--bg-input); color: var(--text-secondary);
        text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.5px;
        padding: 9px 12px; text-align: left; border-bottom: 1px solid var(--border);
    }}
    .pp-table td {{
        padding: 8px 12px; color: var(--text-primary); border-bottom: 1px solid var(--border);
        white-space: nowrap;
    }}
    .pp-table tr:hover td {{ background: var(--bg-hover); }}
    .pp-file-row {{
        display:flex; align-items:center; justify-content:space-between;
        background: var(--bg-input); border: 1px solid var(--border); border-radius: 8px;
        padding: 10px 14px; margin-bottom: 8px;
    }}
    </style>
    """


def inject_css():
    mode = get_mode()
    st.markdown(build_css(PALETTES[mode]), unsafe_allow_html=True)


def data_table_html(rows: list, columns: list) -> str:
    """
    Renders rows (list of dict-like) as a themed HTML table. Used instead of
    st.dataframe, which is canvas-rendered via a fixed base theme and can't
    be recolored by our light/dark toggle at runtime.
    """
    def esc(v):
        return "" if v is None else str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    header_cells = "".join(f"<th>{esc(c)}</th>" for c in columns)
    body_rows = ""
    for r in rows:
        cells = "".join(f"<td>{esc(r[c])}</td>" for c in columns)
        body_rows += f"<tr>{cells}</tr>"
    return (
        '<div class="pp-table-wrap"><table class="pp-table">'
        f"<thead><tr>{header_cells}</tr></thead><tbody>{body_rows}</tbody>"
        "</table></div>"
    )


def field_chip(label: str, value: str):
    """A read-only field display that wraps long values instead of
    truncating them (unlike st.metric), with a title attribute for a
    full-value tooltip on hover."""
    safe_value = (value or "—")
    st.markdown(
        f"""<div class="pp-field-chip" title="{safe_value}">
              <div class="label">{label}</div>
              <div class="value">{safe_value}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def top_bar(viewing_label: str, entities_count: int, sent_today_count: int):
    """
    Rendered as a self-contained HTML component so the clock can tick every
    second in the browser via JS, independent of Streamlit re-runs. Colors
    are passed in explicitly since this lives in its own iframe document.
    """
    mode = get_mode()
    p = PALETTES[mode]
    logo = logo_svg(30, "ppLogoTop")

    html = f"""
    <style>
      html, body {{ margin:0; padding:0; overflow:hidden; box-sizing:border-box; }}
      * {{ box-sizing:border-box; }}
      @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap');
    </style>
    <div style="font-family: 'Manrope','Segoe UI', sans-serif;">
      <div style="display:flex; align-items:center; justify-content:space-between;
                  background:{p['bg_panel']}; border:1px solid {p['border']}; border-radius:12px;
                  padding:12px 22px; flex-wrap:wrap; gap:10px; box-shadow:{p['shadow']};">
        <div style="display:flex; align-items:center; gap:12px; font-weight:600; font-size:1.05rem;">
          <span style="color:{p['text_primary']};">Viewing: <strong>{viewing_label}</strong></span>
        </div>
        <div style="display:flex; align-items:center; gap:22px; color:{p['text_primary']}; font-size:0.95rem;">
          <span id="pp-date">📅 --</span>
          <span id="pp-clock">⏱ --:--:--</span>
          <span style="color:{p['topbar_amber']}; font-weight:600;">Entities&nbsp;: {entities_count}</span>
          <span style="color:{p['topbar_amber']}; font-weight:600;">Sent Today&nbsp;: {sent_today_count}</span>
          <div style="display:flex; align-items:center; gap:8px;">
            {logo}
            <span style="font-weight:800; letter-spacing:0.3px; color:{p['text_primary']}; font-size:0.92rem;">EMSYS</span>
          </div>
        </div>
      </div>
    </div>
    <script>
      function ppUpdateClock() {{
        const now = new Date();
        const pad = (n) => String(n).padStart(2, '0');
        const dateStr = pad(now.getDate()) + '-' + pad(now.getMonth()+1) + '-' + now.getFullYear();
        const timeStr = pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds());
        const dEl = document.getElementById('pp-date');
        const tEl = document.getElementById('pp-clock');
        if (dEl) dEl.innerText = '📅 ' + dateStr;
        if (tEl) tEl.innerText = '⏱ ' + timeStr;
      }}
      ppUpdateClock();
      setInterval(ppUpdateClock, 1000);
    </script>
    """
    if hasattr(st, "iframe"):
        st.iframe(html, height=74)
    elif components is not None:
        components.html(html, height=74)


def welcome_and_breadcrumb(welcome_label: str, current_page: str):
    """
    Renders the 'Welcome: X' line and a clickable 'Home > Current Page'
    breadcrumb, in that order (Home first, then the separator, then the
    current page). Column widths are sized to the actual label length so
    longer page names (e.g. "Manage Entities") don't get truncated.
    Returns the page the user navigated to via the breadcrumb, or None.
    """
    left, right = st.columns([2, 2])
    with left:
        st.markdown(f'<div class="pp-welcome">Welcome: {welcome_label}</div>', unsafe_allow_html=True)

    clicked = None
    with right:
        st.markdown('<div class="pp-breadcrumb-row">', unsafe_allow_html=True)
        if current_page == "Home":
            cols = st.columns([5, 1.2])
            with cols[1]:
                if st.button("Home", key="crumb_home", use_container_width=True):
                    clicked = "Home"
        else:
            home_w = 0.9
            sep_w = 0.3
            current_w = max(1.2, len(current_page) / 9)
            spacer_w = max(0.5, 7 - home_w - sep_w - current_w)
            cols = st.columns([spacer_w, home_w, sep_w, current_w])
            with cols[1]:
                if st.button("Home", key="crumb_home", use_container_width=True):
                    clicked = "Home"
            with cols[2]:
                st.markdown('<div class="pp-breadcrumb-sep">›</div>', unsafe_allow_html=True)
            with cols[3]:
                if st.button(current_page, key="crumb_current", use_container_width=True):
                    clicked = current_page
        st.markdown('</div>', unsafe_allow_html=True)

    return clicked


def card_header(title: str):
    st.markdown(
        f"""<div class="pp-card-header"><span class="info">ⓘ</span> {title}</div>""",
        unsafe_allow_html=True,
    )


def sidebar_nav(current_page: str) -> str:
    with st.sidebar:
        brand_html = (
            f'<div class="pp-brand">{logo_svg(34, "ppLogoSide")}'
            f'<div><span class="pp-brand-title">EMSYS</span>'
            f'<span class="pp-brand-sub">Mail Automation Portal</span></div></div>'
        )
        st.markdown(brand_html, unsafe_allow_html=True)

        selected = current_page
        for page in PAGES:
            active = page == current_page
            wrapper_class = "nav-active" if active else ""
            st.markdown(f'<div class="{wrapper_class}">', unsafe_allow_html=True)
            if st.button(page, key=f"nav_{page}"):
                selected = page
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="pp-sidebar-divider"></div>', unsafe_allow_html=True)
        if "dark_mode" not in st.session_state:
            st.session_state.dark_mode = True
        st.toggle("🌙 Dark mode", key="dark_mode")

    return selected