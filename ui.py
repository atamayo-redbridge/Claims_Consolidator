from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd
import streamlit as st


def apply_global_styles() -> None:
    """Apply all application-wide visual styles."""
    st.markdown(
        """
        <style>
            .block-container {
                max-width: 1180px;
                padding-top: 3.5rem;
                padding-bottom: 3rem;
            }

            .app-title {
                text-align: center;
                font-size: 2.35rem;
                font-weight: 750;
                line-height: 1.25;
                margin-top: 0.75rem;
                margin-bottom: 0.40rem;
                padding-bottom: 0.10rem;
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

            [data-testid="stFileUploader"] {
                max-width: 100%;
            }

            [data-testid="stMetric"] {
                text-align: center;
            }

            [data-testid="stExpander"] {
                border-radius: 10px;
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
            Analyze large claims across multiple companies and groups.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_upload_panel():
    """
    Render the compact upload form.

    Returns:
        uploaded_files, policy_year, analyze_clicked
    """
    left_space, center_column, right_space = st.columns([1, 4, 1])

    with center_column:
        with st.container(border=True):
            uploaded_files = st.file_uploader(
                "Upload Claim Workbooks (MED, RX & DENT)",
                type=["xlsx", "xls"],
                accept_multiple_files=True,
                help=(
                    "Upload one or more MED, RX and DENT claim workbooks. "
                    "Each workbook must contain a worksheet named 'data'."
                ),
            )

            year_label, year_input, analyze_column, row_space = st.columns(
                [1.05, 1.15, 1.15, 2.65],
                vertical_alignment="center",
            )

            with year_label:
                st.markdown("**Policy Year**")

            with year_input:
                policy_year = st.text_input(
                    "Policy Year",
                    placeholder="2025",
                    max_chars=4,
                    label_visibility="collapsed",
                )

            with analyze_column:
                analyze_clicked = st.button(
                    "Analyze",
                    type="primary",
                    use_container_width=True,
                )

    return uploaded_files, policy_year, analyze_clicked


def render_detection_status(packages: dict[str, dict[str, Any]]) -> None:
    """Show the number of detected groups and available contracts."""
    ready_count = sum(
        package["status"] == "ready"
        for package in packages.values()
    )

    st.success(
        f"{len(packages):,} group(s) detected. "
        f"{ready_count:,} contract(s) ready for analysis."
    )


def render_company_analysis_controls(
    packages: dict[str, dict[str, Any]],
    analyses: dict[str, pd.DataFrame],
    analyze_group: Callable[..., pd.DataFrame],
    safe_key: Callable[[str], str],
) -> None:
    """Render company-level group selection and batch analysis buttons."""
    ready_groups = [
        group_number
        for group_number, package in packages.items()
        if package["status"] == "ready"
    ]

    company_groups: dict[str, list[str]] = {}

    for group_number in ready_groups:
        company_name = packages[group_number]["contract"]["company"]
        company_groups.setdefault(company_name, []).append(group_number)

    st.subheader("Analyze by Company")

    st.caption(
        "Choose one, several, or all Group Numbers for each company. "
        "Each group is analyzed independently and keeps its own Excel report."
    )

    for company_name, company_group_numbers in company_groups.items():
        company_key = safe_key(company_name)

        with st.container(border=True):
            st.markdown(f"### {company_name}")

            selected_groups = st.multiselect(
                "Group Numbers to analyze",
                options=company_group_numbers,
                default=company_group_numbers,
                key=f"selected_groups_{company_key}",
            )

            batch_col1, batch_col2, batch_space = st.columns(
                [1.5, 1.25, 3.25]
            )

            with batch_col1:
                analyze_selected = st.button(
                    "Analyze Selected Groups",
                    type="primary",
                    use_container_width=True,
                    disabled=not selected_groups,
                    key=f"analyze_selected_{company_key}",
                )

            with batch_col2:
                analyze_all = st.button(
                    f"Analyze All {len(company_group_numbers)} Groups",
                    use_container_width=True,
                    key=f"analyze_all_{company_key}",
                )

            if analyze_selected or analyze_all:
                groups_to_run = (
                    company_group_numbers
                    if analyze_all
                    else selected_groups
                )

                completed = 0
                errors: list[str] = []

                with st.spinner(
                    f"Analyzing {len(groups_to_run)} group(s) "
                    f"for {company_name}..."
                ):
                    for selected_group in groups_to_run:
                        try:
                            analyses[selected_group] = analyze_group(
                                selected_group
                            )
                            completed += 1
                        except Exception as exc:
                            analyses.pop(selected_group, None)
                            errors.append(
                                f"Group {selected_group}: {exc}"
                            )

                if completed:
                    st.success(
                        f"{completed} group(s) analyzed successfully "
                        f"for {company_name}."
                    )

                for error_message in errors:
                    st.error(error_message)


def _render_contract_metrics(contract: dict[str, Any]) -> None:
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Company", contract["company"])
    col2.metric("Group Number", contract["group_number"])
    col3.metric(
        "Contract Deductible",
        (
            f"${contract['deductible']:,.2f}"
            if contract.get("deductible") is not None
            else "Pending"
        ),
    )
    col4.metric(
        "Maximum Liability",
        (
            f"${contract['maximum_liability']:,.2f}"
            if contract.get("maximum_liability") is not None
            else "Pending"
        ),
    )


def _render_benefit_validation(
    contract: dict[str, Any],
    group_raw: pd.DataFrame,
) -> None:
    st.subheader("Contract Information")

    st.write(
        "**Covered Benefits:** "
        + ", ".join(contract.get("covered_benefits", []))
    )

    uploaded_benefits = sorted(
        group_raw["Benefit"].dropna().unique().tolist()
    )
    required_benefits = set(contract.get("covered_benefits", []))
    uploaded_set = set(uploaded_benefits)

    missing_benefits = sorted(required_benefits - uploaded_set)
    noncovered_uploaded = sorted(uploaded_set - required_benefits)

    if missing_benefits:
        st.warning(
            "Covered claim files not detected: "
            + ", ".join(missing_benefits)
        )
    else:
        st.info("All configured covered benefits were detected.")

    if noncovered_uploaded:
        st.warning(
            "Uploaded benefit types not covered by this contract: "
            + ", ".join(noncovered_uploaded)
            + ". They will be excluded from this group's analysis."
        )


def _render_member_rules(contract: dict[str, Any]) -> None:
    member_rules = contract.get("member_rules", {})
    laser_rows = []
    excluded_rows = []

    for member_id, rule in member_rules.items():
        if rule.get("type") == "laser":
            laser_rows.append(
                {
                    "Member ID": member_id,
                    "Laser Deductible": rule["deductible"],
                }
            )
        elif rule.get("type") == "excluded":
            excluded_rows.append(
                {
                    "Member ID": member_id,
                    "Rule": "No Coverage",
                }
            )

    left, right = st.columns(2)

    with left:
        st.markdown("#### Laser Members")
        if laser_rows:
            st.dataframe(
                pd.DataFrame(laser_rows),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Laser Deductible": st.column_config.NumberColumn(
                        format="$%.2f"
                    )
                },
            )
        else:
            st.write("None")

    with right:
        st.markdown("#### Excluded Members")
        if excluded_rows:
            st.dataframe(
                pd.DataFrame(excluded_rows),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.write("None")

    if contract.get("notes"):
        st.warning(contract["notes"])


def _render_analysis_results(analysis: pd.DataFrame) -> None:
    st.divider()
    st.subheader("Analysis Results")

    total_claims = float(analysis["Total Claims"].sum())
    redbridge_liability = float(
        analysis["Redbridge Liability"].sum()
    )
    large_claim_count = int(
        (analysis["Redbridge Liability"] > 0).sum()
    )
    excluded_count = int(
        (
            analysis["Coverage Status"]
            == "Excluded - No Coverage"
        ).sum()
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Claims", f"${total_claims:,.2f}")
    c2.metric(
        "Redbridge Liability",
        f"${redbridge_liability:,.2f}",
    )
    c3.metric(
        "Members Above Deductible",
        f"{large_claim_count:,}",
    )
    c4.metric(
        "Excluded Members Found",
        f"{excluded_count:,}",
    )

    st.dataframe(
        analysis,
        use_container_width=True,
        hide_index=True,
        column_config={
            "MED": st.column_config.NumberColumn(format="$%.2f"),
            "RX": st.column_config.NumberColumn(format="$%.2f"),
            "DENT": st.column_config.NumberColumn(format="$%.2f"),
            "DENTAL": st.column_config.NumberColumn(format="$%.2f"),
            "VISION": st.column_config.NumberColumn(format="$%.2f"),
            "Total Claims": st.column_config.NumberColumn(
                format="$%.2f"
            ),
            "Contract Laser": st.column_config.NumberColumn(
                format="$%.2f"
            ),
            "Applicable Deductible": st.column_config.NumberColumn(
                format="$%.2f"
            ),
            "Maximum Redbridge Liability":
                st.column_config.NumberColumn(format="$%.2f"),
            "Redbridge Liability":
                st.column_config.NumberColumn(format="$%.2f"),
            "Above Coverage Limit":
                st.column_config.NumberColumn(format="$%.2f"),
            "Exceeds Deductible":
                st.column_config.CheckboxColumn(),
        },
    )


def render_group_sections(
    packages: dict[str, dict[str, Any]],
    analyses: dict[str, pd.DataFrame],
    analyze_group: Callable[..., pd.DataFrame],
    report_builder: Callable[..., bytes],
    safe_key: Callable[[str], str],
) -> None:
    """Render every group, its options, results, and Excel download."""
    st.divider()
    st.subheader("Group Details and Separate Reports")

    for group_number, package in packages.items():
        if package["status"] != "ready":
            with st.expander(
                f"Group {group_number} — Contract not available",
                expanded=True,
            ):
                st.error(package["error"])
            continue

        contract = package["contract"]
        group_raw = package["raw_claims"]
        group_key = safe_key(group_number)
        title = f"{contract['company']} — Group {group_number}"

        with st.expander(title, expanded=True):
            _render_contract_metrics(contract)
            _render_benefit_validation(contract, group_raw)
            _render_member_rules(contract)

            with st.container(border=True):
                st.subheader("Analysis Options")

                alternative_text = st.text_input(
                    "Optional Alternative Deductible",
                    placeholder=(
                        "Leave blank to use the contract deductible"
                    ),
                    help="Enter numbers only, for example 75000.",
                    key=f"alternative_{group_key}",
                )

                laser_mode = st.radio(
                    "When an alternative deductible is entered:",
                    options=[
                        "Keep contract lasers",
                        "Replace all deductibles, including lasers",
                    ],
                    horizontal=True,
                    key=f"laser_mode_{group_key}",
                )

                run_final = st.button(
                    f"Run Analysis for Group {group_number}",
                    type="primary",
                    use_container_width=False,
                    key=f"run_{group_key}",
                )

            if run_final:
                try:
                    alternative = None

                    if alternative_text.strip():
                        cleaned = (
                            alternative_text
                            .replace("$", "")
                            .replace(",", "")
                            .strip()
                        )
                        alternative = float(cleaned)

                        if alternative < 0:
                            raise ValueError(
                                "The Alternative Deductible "
                                "cannot be negative."
                            )

                    analyses[group_number] = analyze_group(
                        group_number,
                        alternative_deductible=alternative,
                        replace_lasers=(
                            laser_mode
                            == "Replace all deductibles, including lasers"
                        ),
                    )
                except Exception as exc:
                    analyses.pop(group_number, None)
                    st.error(str(exc))

            analysis = analyses.get(group_number)

            if analysis is not None:
                _render_analysis_results(analysis)

                report_bytes = report_builder(
                    analysis=analysis,
                    raw_claims=group_raw,
                    contract=contract,
                )

                safe_company = safe_key(contract["company"])
                filename = (
                    f"{safe_company}_"
                    f"{contract['group_number']}_"
                    f"{contract['policy_year']}_"
                    f"Large_Claims.xlsx"
                )

                st.download_button(
                    f"Download Excel Report — {contract['company']}",
                    data=report_bytes,
                    file_name=filename,
                    mime=(
                        "application/vnd.openxmlformats-"
                        "officedocument.spreadsheetml.sheet"
                    ),
                    use_container_width=False,
                    key=f"download_{group_key}",
                )
