from __future__ import annotations

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

st.title("Redbridge Large Claims Analyzer")

st.caption(
    "Upload claim workbooks, enter the policy year, consolidate claims "
    "by Member ID, and calculate Redbridge liability."
)


# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------

if "raw_claims" not in st.session_state:
    st.session_state.raw_claims = None

if "consolidated" not in st.session_state:
    st.session_state.consolidated = None

if "contract" not in st.session_state:
    st.session_state.contract = None

if "analysis" not in st.session_state:
    st.session_state.analysis = None


# ---------------------------------------------------------
# FILE UPLOAD AND POLICY YEAR
# ---------------------------------------------------------

with st.container(border=True):

    uploaded_files = st.file_uploader(
        "Upload claim workbooks",
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        help="Each workbook must contain a sheet named 'data'.",
    )

    policy_year = st.text_input(
        "Policy Year",
        placeholder="Example: 2025",
        max_chars=4,
    )

    analyze_clicked = st.button(
        "Analyze",
        type="primary",
        use_container_width=True,
    )


# ---------------------------------------------------------
# INITIAL ANALYSIS
# ---------------------------------------------------------

if analyze_clicked:

    st.session_state.analysis = None

    try:

        year = policy_year.strip()

        if not year.isdigit() or len(year) != 4:
            raise ValueError(
                "Enter a valid four-digit Policy Year."
            )

        raw_claims = read_all_claim_files(
            uploaded_files or []
        )

        group_number = str(
            raw_claims["Group Number"].iloc[0]
        )

        contract = get_contract(
            group_number,
            year,
        )

        consolidated = consolidate_claims(
            raw_claims
        )

        st.session_state.raw_claims = raw_claims
        st.session_state.consolidated = consolidated
        st.session_state.contract = contract

    except Exception as exc:

        st.session_state.raw_claims = None
        st.session_state.consolidated = None
        st.session_state.contract = None

        st.error(str(exc))


# ---------------------------------------------------------
# CONTRACT INFORMATION
# ---------------------------------------------------------

contract = st.session_state.contract

if contract:

    st.success("Contract found.")

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
            contract.get(
                "covered_benefits",
                [],
            )
        )
    )


    # -----------------------------------------------------
    # BENEFIT FILE VALIDATION
    # -----------------------------------------------------

    uploaded_benefits = sorted(
        st.session_state.raw_claims[
            "Benefit"
        ]
        .dropna()
        .unique()
        .tolist()
    )

    required_benefits = set(
        contract.get(
            "covered_benefits",
            [],
        )
    )

    uploaded_set = set(
        uploaded_benefits
    )

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
            + ". They will be excluded from the contract analysis."
        )


    # -----------------------------------------------------
    # LASERS AND EXCLUDED MEMBERS
    # -----------------------------------------------------

    member_rules = contract.get(
        "member_rules",
        {},
    )

    laser_rows = []
    excluded_rows = []

    for member_id, rule in member_rules.items():

        if rule.get("type") == "laser":

            laser_rows.append(
                {
                    "Member ID": member_id,
                    "Laser Deductible": rule[
                        "deductible"
                    ],
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

        st.markdown(
            "#### Laser Members"
        )

        if laser_rows:

            laser_df = pd.DataFrame(
                laser_rows
            )

            st.dataframe(
                laser_df,
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

        st.markdown(
            "#### Excluded Members"
        )

        if excluded_rows:

            st.dataframe(
                pd.DataFrame(
                    excluded_rows
                ),
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.write("None")


    if contract.get("notes"):

        st.warning(
            contract["notes"]
        )


    # -----------------------------------------------------
    # ANALYSIS OPTIONS
    # -----------------------------------------------------

    with st.container(border=True):

        st.subheader(
            "Analysis Options"
        )

        alternative_text = st.text_input(
            "Optional Alternative Deductible",
            placeholder=(
                "Leave blank to use the contract deductible"
            ),
            help=(
                "Enter numbers only, for example 75000."
            ),
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
        )

        run_final = st.button(
            "Run Final Analysis",
            type="primary",
            use_container_width=True,
        )


    # -----------------------------------------------------
    # FINAL CALCULATION
    # -----------------------------------------------------

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

                alternative = float(
                    cleaned
                )

                if alternative < 0:

                    raise ValueError(
                        "The Alternative Deductible "
                        "cannot be negative."
                    )


            covered = set(
                contract.get(
                    "covered_benefits",
                    [],
                )
            )

            filtered_raw = (
                st.session_state.raw_claims[
                    st.session_state.raw_claims[
                        "Benefit"
                    ].isin(covered)
                ]
                .copy()
            )

            if filtered_raw.empty:

                raise ValueError(
                    "None of the uploaded claims "
                    "belong to a covered benefit."
                )


            filtered_consolidated = (
                consolidate_claims(
                    filtered_raw
                )
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

            st.session_state.analysis = analysis

        except Exception as exc:

            st.session_state.analysis = None

            st.error(str(exc))


# ---------------------------------------------------------
# ANALYSIS RESULTS
# ---------------------------------------------------------

analysis = st.session_state.analysis

if analysis is not None:

    st.divider()

    st.subheader(
        "Analysis Results"
    )


    total_claims = float(
        analysis[
            "Total Claims"
        ].sum()
    )

    redbridge_liability = float(
        analysis[
            "Redbridge Liability"
        ].sum()
    )

    large_claim_count = int(
        (
            analysis[
                "Redbridge Liability"
            ] > 0
        ).sum()
    )

    excluded_count = int(
        (
            analysis[
                "Coverage Status"
            ]
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


    # -----------------------------------------------------
    # EXCEL DOWNLOAD
    # -----------------------------------------------------

    report_bytes = build_excel_report(
        analysis=analysis,
        raw_claims=st.session_state.raw_claims,
        contract=st.session_state.contract,
    )


    safe_company = (
        st.session_state.contract[
            "company"
        ]
        .replace(" ", "_")
        .replace("/", "_")
    )


    filename = (
        f"{safe_company}_"
        f"{st.session_state.contract['group_number']}_"
        f"{st.session_state.contract['policy_year']}_"
        f"Large_Claims.xlsx"
    )


    st.download_button(
        "Download Excel Report",
        data=report_bytes,
        file_name=filename,
        mime=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),
        use_container_width=True,
    )
