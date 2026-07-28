from __future__ import annotations

from copy import deepcopy

import pandas as pd
import streamlit as st

from claims_engine import apply_contract_rules, consolidate_claims
from claims_reader import read_all_claim_files
from contracts import get_contract
from excel_report import build_excel_report


st.set_page_config(
    page_title="Redbridge Large Claims Analyzer",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1180px;
            padding-top: 2.5rem;
            padding-bottom: 3rem;
        }

        .app-title {
            text-align: center;
            font-size: 2.35rem;
            font-weight: 750;
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
        }

        [data-testid="stFileUploader"] {
            max-width: 100%;
        }

        [data-testid="stMetric"] {
            text-align: center;
        }
    </style>

    <div class="app-title">Redbridge Large Claims Analyzer</div>
    <div class="app-subtitle">
        Upload claim workbooks, enter the policy year, consolidate claims by
        Member ID, and calculate Redbridge liability independently for each
        company and group.
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

BENEFIT_ALIASES = {
    "MED": "MED",
    "MEDICAL": "MED",
    "RX": "RX",
    "PHARMACY": "RX",
    "PRESCRIPTION": "RX",
    "DENT": "DENT",
    "DENTAL": "DENT",
    "VISION": "VISION",
    "VIS": "VISION",
}


def normalize_benefit(value):
    """Standardize benefit names used by files and contracts."""
    if pd.isna(value):
        return None

    text = str(value).strip().upper()
    return BENEFIT_ALIASES.get(text, text)


def clean_group_number(value) -> str:
    """Prevent group numbers read from Excel from appearing as 750109.0."""
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if text.endswith(".0"):
        text = text[:-2]

    return text


def normalize_contract(contract: dict) -> dict:
    """
    Work with DENT internally, even when contracts.py still contains DENTAL.
    This avoids changing the original contract dictionary in memory.
    """
    normalized = deepcopy(contract)

    normalized["group_number"] = clean_group_number(
        normalized.get("group_number", "")
    )

    normalized["covered_benefits"] = [
        normalize_benefit(benefit)
        for benefit in normalized.get("covered_benefits", [])
    ]

    return normalized


def safe_key(value: str) -> str:
    return (
        str(value)
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(".", "_")
    )


# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------

if "raw_claims" not in st.session_state:
    st.session_state.raw_claims = None

if "group_packages" not in st.session_state:
    st.session_state.group_packages = {}

if "group_analyses" not in st.session_state:
    st.session_state.group_analyses = {}


# ---------------------------------------------------------
# FILE UPLOAD AND POLICY YEAR
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# INITIAL ANALYSIS — MULTIPLE GROUPS
# ---------------------------------------------------------

if analyze_clicked:

    st.session_state.raw_claims = None
    st.session_state.group_packages = {}
    st.session_state.group_analyses = {}

    try:

        year = policy_year.strip()

        if not year.isdigit() or len(year) != 4:
            raise ValueError("Enter a valid four-digit Policy Year.")

        if not uploaded_files:
            raise ValueError("Upload at least one claim workbook.")

        raw_claims = read_all_claim_files(uploaded_files)

        required_columns = {"Group Number", "Member ID", "Benefit"}

        missing_columns = required_columns - set(raw_claims.columns)

        if missing_columns:
            raise ValueError(
                "The combined claim data is missing required columns: "
                + ", ".join(sorted(missing_columns))
            )

        raw_claims = raw_claims.copy()

        raw_claims["Group Number"] = raw_claims[
            "Group Number"
        ].apply(clean_group_number)

        raw_claims["Benefit"] = raw_claims[
            "Benefit"
        ].apply(normalize_benefit)

        raw_claims = raw_claims[
            raw_claims["Group Number"] != ""
        ].copy()

        if raw_claims.empty:
            raise ValueError(
                "No valid Group Number was found in the uploaded files."
            )

        group_numbers = sorted(
            raw_claims["Group Number"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        packages = {}

        for group_number in group_numbers:

            group_raw = raw_claims[
                raw_claims["Group Number"] == group_number
            ].copy()

            try:
                contract = normalize_contract(
                    get_contract(group_number, year)
                )

                consolidated = consolidate_claims(group_raw)

                packages[group_number] = {
                    "status": "ready",
                    "raw_claims": group_raw,
                    "consolidated": consolidated,
                    "contract": contract,
                    "error": None,
                }

            except Exception as group_exc:

                packages[group_number] = {
                    "status": "error",
                    "raw_claims": group_raw,
                    "consolidated": None,
                    "contract": None,
                    "error": str(group_exc),
                }

        st.session_state.raw_claims = raw_claims
        st.session_state.group_packages = packages

    except Exception as exc:

        st.error(str(exc))


# ---------------------------------------------------------
# RESULTS BY COMPANY / GROUP
# ---------------------------------------------------------

packages = st.session_state.group_packages

if packages:

    ready_count = sum(
        package["status"] == "ready"
        for package in packages.values()
    )

    st.success(
        f"{len(packages):,} group(s) detected. "
        f"{ready_count:,} contract(s) ready for analysis."
    )

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

        title = (
            f"{contract['company']} — "
            f"Group {group_number}"
        )

        with st.expander(title, expanded=True):

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "Company",
                contract["company"],
            )

            col2.metric(
                "Group Number",
                contract["group_number"],
            )

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

            st.subheader("Contract Information")

            st.write(
                "**Covered Benefits:** "
                + ", ".join(
                    contract.get("covered_benefits", [])
                )
            )

            # -------------------------------------------------
            # BENEFIT VALIDATION FOR THIS GROUP ONLY
            # -------------------------------------------------

            uploaded_benefits = sorted(
                group_raw["Benefit"]
                .dropna()
                .unique()
                .tolist()
            )

            required_benefits = set(
                contract.get("covered_benefits", [])
            )

            uploaded_set = set(uploaded_benefits)

            missing_benefits = sorted(
                required_benefits - uploaded_set
            )

            noncovered_uploaded = sorted(
                uploaded_set - required_benefits
            )

            if missing_benefits:
                st.warning(
                    "Covered claim files not detected: "
                    + ", ".join(missing_benefits)
                )
            else:
                st.info(
                    "All configured covered benefits were detected."
                )

            if noncovered_uploaded:
                st.warning(
                    "Uploaded benefit types not covered by this contract: "
                    + ", ".join(noncovered_uploaded)
                    + ". They will be excluded from this group's analysis."
                )

            # -------------------------------------------------
            # LASERS AND EXCLUDED MEMBERS
            # -------------------------------------------------

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
                            "Laser Deductible":
                            st.column_config.NumberColumn(
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

            # -------------------------------------------------
            # INDEPENDENT ANALYSIS OPTIONS
            # -------------------------------------------------

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
                        (
                            "Replace all deductibles, "
                            "including lasers"
                        ),
                    ],
                    horizontal=True,
                    key=f"laser_mode_{group_key}",
                )

                run_final = st.button(
                    f"Run Analysis for {contract['company']}",
                    type="primary",
                    use_container_width=False,
                    key=f"run_{group_key}",
                )

            # -------------------------------------------------
            # FINAL CALCULATION FOR THIS GROUP
            # -------------------------------------------------

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

                    covered = set(
                        contract.get("covered_benefits", [])
                    )

                    filtered_raw = group_raw[
                        group_raw["Benefit"].isin(covered)
                    ].copy()

                    if filtered_raw.empty:
                        raise ValueError(
                            "None of the uploaded claims for this group "
                            "belong to a covered benefit."
                        )

                    filtered_consolidated = consolidate_claims(
                        filtered_raw
                    )

                    analysis = apply_contract_rules(
                        filtered_consolidated,
                        contract,
                        alternative_deductible=alternative,
                        replace_lasers=(
                            laser_mode
                            == (
                                "Replace all deductibles, "
                                "including lasers"
                            )
                        ),
                    )

                    st.session_state.group_analyses[
                        group_number
                    ] = analysis

                except Exception as exc:

                    st.session_state.group_analyses.pop(
                        group_number,
                        None,
                    )

                    st.error(str(exc))

            # -------------------------------------------------
            # ANALYSIS RESULTS FOR THIS GROUP
            # -------------------------------------------------

            analysis = st.session_state.group_analyses.get(
                group_number
            )

            if analysis is not None:

                st.divider()
                st.subheader("Analysis Results")

                total_claims = float(
                    analysis["Total Claims"].sum()
                )

                redbridge_liability = float(
                    analysis["Redbridge Liability"].sum()
                )

                large_claim_count = int(
                    (
                        analysis["Redbridge Liability"] > 0
                    ).sum()
                )

                excluded_count = int(
                    (
                        analysis["Coverage Status"]
                        == "Excluded - No Coverage"
                    ).sum()
                )

                c1, c2, c3, c4 = st.columns(4)

                c1.metric(
                    "Total Claims",
                    f"${total_claims:,.2f}",
                )

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
                        "MED":
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        ),
                        "RX":
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        ),
                        "DENT":
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        ),
                        # Kept for compatibility with older reports.
                        "DENTAL":
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        ),
                        "VISION":
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        ),
                        "Total Claims":
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        ),
                        "Contract Laser":
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        ),
                        "Applicable Deductible":
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        ),
                        "Maximum Redbridge Liability":
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        ),
                        "Redbridge Liability":
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        ),
                        "Above Coverage Limit":
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        ),
                        "Exceeds Deductible":
                        st.column_config.CheckboxColumn(),
                    },
                )

                # ---------------------------------------------
                # EXCEL DOWNLOAD FOR THIS GROUP
                # ---------------------------------------------

                report_bytes = build_excel_report(
                    analysis=analysis,
                    raw_claims=group_raw,
                    contract=contract,
                )

                safe_company = safe_key(
                    contract["company"]
                )

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
