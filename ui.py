from __future__ import annotations

import streamlit as st


def apply_global_styles() -> None:
    """Apply the visual style used throughout the application."""
    st.markdown(
        """
        <style>
            .block-container {
                max-width: 1180px;
                padding-top: 2.25rem;
                padding-bottom: 3rem;
            }

            .app-title {
                text-align: center;
                font-size: 2.35rem;
                font-weight: 750;
                line-height: 1.2;
                margin-bottom: 0.35rem;
            }

            .app-subtitle {
                text-align: center;
                color: #6b7280;
                font-size: 0.95rem;
                margin-bottom: 1.8rem;
            }

            div.stButton,
            div.stDownloadButton {
                display: flex;
                justify-content: center;
            }

            div.stButton > button,
            div.stDownloadButton > button {
                width: auto !important;
                min-width: 180px;
                padding-left: 1.5rem;
                padding-right: 1.5rem;
                border-radius: 8px;
            }

            [data-testid="stMetric"] {
                text-align: center;
            }

            [data-testid="stFileUploader"] {
                width: 100%;
            }

            [data-testid="stExpander"] {
                border-radius: 10px;
            }

            .section-label {
                font-size: 1.05rem;
                font-weight: 650;
                margin-bottom: 0.4rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    """Render the application title and subtitle."""
    st.markdown(
        """
        <div class="app-title">Redbridge Large Claims Analyzer</div>
        <div class="app-subtitle">
            Upload claim workbooks, enter the policy year, consolidate claims
            by Member ID, and calculate Redbridge liability independently for
            each company and group.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_upload_panel():
    """
    Render the centered upload controls.

    Returns:
        tuple: uploaded_files, policy_year, analyze_clicked
    """
    left_space, center_column, right_space = st.columns(
        [1, 4, 1]
    )

    with center_column:
        with st.container(border=True):
            uploaded_files = st.file_uploader(
                "Upload claim workbooks",
                type=["xlsx", "xls"],
                accept_multiple_files=True,
                help="Each workbook must contain a sheet named 'data'.",
            )

            year_left, year_center, year_right = st.columns(
                [1, 2, 1]
            )

            with year_center:
                policy_year = st.text_input(
                    "Policy Year",
                    placeholder="Example: 2025",
                    max_chars=4,
                )

            analyze_clicked = st.button(
                "Analyze",
                type="primary",
                use_container_width=False,
            )

    return uploaded_files, policy_year, analyze_clicked
