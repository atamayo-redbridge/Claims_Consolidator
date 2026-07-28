from __future__ import annotations

from copy import deepcopy

import pandas as pd
import streamlit as st

from claims_engine import apply_contract_rules, consolidate_claims
from claims_reader import read_all_claim_files
from contracts import get_contract
from excel_report import build_excel_report
from ui import (
    apply_global_styles,
    render_company_analysis_controls,
    render_detection_status,
    render_group_sections,
    render_header,
    render_upload_panel,
)


st.set_page_config(
    page_title="Redbridge Large Claims Analyzer",
    page_icon="📊",
    layout="wide",
)

apply_global_styles()
render_header()


# ---------------------------------------------------------
# DATA NORMALIZATION HELPERS
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
    """Prevent group numbers from appearing as 750109.0."""
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if text.endswith(".0"):
        text = text[:-2]

    return text


def normalize_contract(contract: dict) -> dict:
    """Normalize contract group and benefit names."""
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
    """Create a Streamlit-safe widget key."""
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
# BUSINESS LOGIC
# ---------------------------------------------------------

def calculate_group_analysis(
    group_number: str,
    alternative_deductible=None,
    replace_lasers: bool = False,
) -> pd.DataFrame:
    """Analyze one Group Number independently."""
    package = st.session_state.group_packages[group_number]

    if package["status"] != "ready":
        raise ValueError(package["error"])

    contract = package["contract"]
    group_raw = package["raw_claims"]
    covered = set(contract.get("covered_benefits", []))

    filtered_raw = group_raw[
        group_raw["Benefit"].isin(covered)
    ].copy()

    if filtered_raw.empty:
        raise ValueError(
            f"None of the uploaded claims for Group {group_number} "
            "belong to a covered benefit."
        )

    filtered_consolidated = consolidate_claims(filtered_raw)

    return apply_contract_rules(
        filtered_consolidated,
        contract,
        alternative_deductible=alternative_deductible,
        replace_lasers=replace_lasers,
    )


def load_group_packages(uploaded_files, policy_year: str) -> None:
    """Read files, normalize data, and prepare one package per group."""
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


# ---------------------------------------------------------
# APPLICATION FLOW
# ---------------------------------------------------------

uploaded_files, policy_year, analyze_clicked = render_upload_panel()

if analyze_clicked:
    st.session_state.raw_claims = None
    st.session_state.group_packages = {}
    st.session_state.group_analyses = {}

    try:
        load_group_packages(uploaded_files, policy_year)
    except Exception as exc:
        st.error(str(exc))

packages = st.session_state.group_packages

if packages:
    render_detection_status(packages)

    render_company_analysis_controls(
        packages=packages,
        analyses=st.session_state.group_analyses,
        analyze_group=calculate_group_analysis,
        safe_key=safe_key,
    )

    render_group_sections(
        packages=packages,
        analyses=st.session_state.group_analyses,
        analyze_group=calculate_group_analysis,
        report_builder=build_excel_report,
        safe_key=safe_key,
    )
