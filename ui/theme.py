"""Theme utilities for the Streamlit chess UI."""

from __future__ import annotations

import textwrap

import streamlit as st


def apply_theme(theme_name: str) -> None:
    """Inject CSS variables and animations to customize the app."""

    base_font = "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif"
    if theme_name == "Sombre":
        palette = {
            "bg": "#0f172a",
            "panel": "#1e293b",
            "text": "#e2e8f0",
            "accent": "#22d3ee",
            "muted": "#94a3b8",
        }
    else:
        palette = {
            "bg": "#f4f5fb",
            "panel": "#ffffff",
            "text": "#0f172a",
            "accent": "#2563eb",
            "muted": "#475569",
        }

    styles = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
        :root {{
            --bg-color: {palette['bg']};
            --panel-color: {palette['panel']};
            --text-color: {palette['text']};
            --accent-color: {palette['accent']};
            --muted-color: {palette['muted']};
            --base-font: {base_font};
        }}

        body, .stApp {{
            font-family: var(--base-font);
            background: var(--bg-color);
            color: var(--text-color);
        }}

        section[data-testid="stSidebar"], .main, .block-container {{
            background: var(--bg-color);
        }}

        .stButton>button, .stDownloadButton>button {{
            border-radius: 10px;
            transition: transform 150ms ease, box-shadow 150ms ease;
            box-shadow: 0 6px 24px rgba(0,0,0,0.06);
            border: 1px solid rgba(0,0,0,0.04);
        }}

        .stButton>button:hover, .stDownloadButton>button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 28px rgba(0,0,0,0.08);
        }}

        .stButton>button:focus-visible {{
            outline: 2px solid var(--accent-color);
        }}

        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {{
            color: var(--text-color);
            letter-spacing: 0.01em;
        }}

        .stAlert {{
            border-left: 4px solid var(--accent-color);
            border-radius: 12px;
        }}

        .stCaption {{
            color: var(--muted-color);
        }}

        /* Chessboard styling */
        .chessboard {{
            padding: 10px;
            border-radius: 16px;
            background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.04), transparent 40%),
                        var(--panel-color);
            box-shadow: 0 10px 30px rgba(0,0,0,0.12);
            border: 1px solid rgba(0,0,0,0.08);
        }}

        .chessboard .stForm > div {{
            gap: 4px !important;
        }}

        .chessboard .stButton>button {{
            height: 72px;
            font-size: 30px;
            font-weight: 600;
            border-radius: 10px;
            border: none;
            transition: transform 120ms ease, box-shadow 120ms ease, filter 120ms ease;
        }}

        .chessboard .stButton>button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.12);
        }}

        .chessboard .stButton>button:focus-visible {{
            outline: 3px solid var(--accent-color);
            filter: brightness(1.05);
        }}
    </style>
    """

    st.markdown(textwrap.dedent(styles), unsafe_allow_html=True)
