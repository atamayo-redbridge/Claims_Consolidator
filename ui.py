from __future__ import annotations

import streamlit as st


def apply_global_styles() -> None:
    """Apply the global visual style for the application."""

    st.markdown(
        """
        <style>

            /* Main page container */
            .block-container {
                max-width: 1320px;
                padding-top: 5rem;
                padding-bottom: 3rem;
                padding-left: 2rem;
                padding-right: 2rem;
            }

            /* Main title */
            .app-title {
                text-align: center;
                font-size: 2.45rem;
                font-weight: 750;
                line-height: 1.5;
                padding-top: 0.75rem;
                margin-top: 0.5rem;
                margin-bottom: 0.35rem;
                letter-spacing: -0.02em;
                overflow: visible;
            }

            /* Subtitle */
            .app-subtitle {
                max-width: 980px;
                margin: 0 auto 1.8rem auto;
                text-align: center;
                color: #6b7280;
                font-size: 0.96rem;
                line-height: 1.55;
            }

            /* Upload card title */
            .upload-card-title {
                font-size: 1.05rem;
                font-weight: 650;
                margin-bottom: 0.35rem;
            }

            /* Upload card description */
            .upload-card-caption {
                color: #6b7280;
                font-size: 0.86rem;
                margin-bottom: 0.9rem;
            }

            /* Rounded containers */
            [data-testid="stVerticalBlockBorderWrapper"] {
                border-radius: 14px;
            }

            /* Expanders */
            [data-testid="stExpander"] {
                border-radius: 12px;
                overflow: hidden;
            }

            /* File uploader */
            [data-testid="stFileUploader"] {
                width: 100%;
            }

            [data-testid="stFileUploaderDropzone"] {
                border-radius: 10px;
                min-height: 92px;
            }

            /* Text input */
            [data-testid="stTextInput"] input {
                border-radius: 9px;
                min-height: 42px;
            }

            /* Buttons */
            [data-testid="stButton"] button,
            [data-testid="stDownloadButton"] button {
                border-radius: 9px;
                min-height: 42px;
                font-weight: 600;
                padding-left: 1.4rem;
                padding-right: 1.4rem;
            }

            /* Metrics */
            [data-testid="stMetric"] {
                text-align: center;
                padding: 0.4rem 0.2rem;
            }

            [data-testid="stMetricLabel"] {
                justify-content: center;
            }

            /* Tables */
            [data-testid="stDataFrame"] {
                border-radius: 10px;
                overflow: hidden;
            }

            /* Mobile screens */
            @media (max-width: 900px) {

                .block-container {
                    padding-top: 3.5rem;
                    padding-left: 1rem;
                    padding-right: 1rem;
                }

                .app-title {
                    font-size: 2rem;
                    line-height: 1.5;
                    padding-top: 0.5rem;
                }

                .app-subtitle {
                    font-size: 0.9rem;
                }
            }

        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    """Render the page title and subtitle."""

    st.markdown(
        """
        <div class="app-title">
            Redbridge Large Claims Analyzer
        </div>

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
    Render the upload form.

    Returns:
        uploaded_files
        policy_year
        analyze_clicked
    """

    outer_left, main_column, outer_right = st.columns(
        [1.15, 4.7, 1.15]
    )

    with main_column:

        with st.container(border=True):

            st.markdown(
                """
                <div class="upload-card-title">
                    Claim Workbooks
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                """
                <div class="upload-card-caption">
                    Upload one or more Excel claim files.
                    Each workbook must contain a sheet named
                    <strong>data</strong>.
                </div>
                """,
                unsafe_allow_html=True,
            )

            uploaded_files = st.file_uploader(
                "Upload claim workbooks",
                type=["xlsx", "xls"],
                accept_multiple_files=True,
                label_visibility="collapsed",
                help="Each workbook must contain a sheet named 'data'.",
            )

            st.write("")

            control_column, empty_space = st.columns(
                [1.25, 2.75]
            )

            with control_column:

                policy_year = st.text_input(
                    "Policy Year",
                    placeholder="Example: 2025",
                    max_chars=4,
                )

                analyze_clicked = st.button(
                    "Analyze",
                    type="primary",
                    use_container_width=True,
                    key="analyze_main",
                )

    return (
        uploaded_files,
        policy_year,
        analyze_clicked,
    )


def render_action_button(
    label: str,
    *,
    key: str,
    button_type: str = "primary",
) -> bool:
    """
    Render a compact action button aligned to the left.
    """

    button_column, empty_space = st.columns(
        [1.25, 2.75]
    )

    with button_column:

        return st.button(
            label,
            type=button_type,
            use_container_width=True,
            key=key,
        )


def render_download_button(
    label: str,
    *,
    data,
    file_name: str,
    mime: str,
    key: str,
) -> None:
    """
    Render a compact download button aligned to the left.
    """

    button_column, empty_space = st.columns(
        [1.5, 2.5]
    )

    with button_column:

        st.download_button(
            label,
            data=data,
            file_name=file_name,
            mime=mime,
            use_container_width=True,
            key=key,
        )
