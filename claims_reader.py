from __future__ import annotations

import io
import re
from pathlib import Path
from typing import BinaryIO

import pandas as pd


GROUP_CANDIDATES = [
    "GROUP NUMBER",
    "GROUPNUMBER",
    "GRPNUM",
    "GROUP",
    "GROUP NO",
    "GROUP #",
    "COMPANY GROUP NUMBER",
]

MEMBER_CANDIDATES = [
    "MEMBER ID NUMBER",
    "MEMBERIDNUMBER",
    "MEMBER ID",
    "MEMBERID",
    "MEMBNO",
    "MEMBER NUMBER",
    "MEMBER NO",
    "CERTIFICATE NUMBER",
    "CERTIFICATE NO",
]

AMOUNT_CANDIDATES = [
    "AMOUNT PAID",
    "PAID AMOUNT",
    "COMPUTED",
    "PAID CLAIM AMOUNT",
    "TOTAL PAID",
    "CLAIM AMOUNT",
    "NET PAID",
    "PAYMENT AMOUNT",
    "AMOUNT",
    "PAID",
]

FIRST_NAME_CANDIDATES = [
    "MEMB FIRST NAME",
    "MEMBER FIRST NAME",
    "MEMBER FIRSTNAME",
    "PATIENT FIRST NAME",
    "SUBSCRIBER FIRST NAME",
    "FIRST NAME",
    "FIRSTNAME",
    "FSTNAM",
    "FNAME",
]

LAST_NAME_CANDIDATES = [
    "MEMB LAST NAME",
    "MEMB LAS NAME",
    "MEMBER LAST NAME",
    "MEMBER LASTNAME",
    "PATIENT LAST NAME",
    "SUBSCRIBER LAST NAME",
    "LAST NAME",
    "LASTNAME",
    "LSTNAM",
    "LNAME",
]


def _clean_header(value: object) -> str:
    """
    Normalize a column header for reliable matching.

    Example:
        "Memb First_Name" -> "MEMBFIRSTNAME"
    """
    if pd.isna(value):
        return ""

    return re.sub(
        r"[^A-Z0-9]+",
        "",
        str(value).strip().upper(),
    )


def _find_column(columns, candidates):
    """
    Find a column safely.

    Exact normalized matches are preferred. Limited fallback matching is used
    only for longer candidate names to avoid selecting provider-name columns
    such as Fstnam2 or Lstnam2.
    """
    normalized_columns = {
        _clean_header(column): column
        for column in columns
        if _clean_header(column)
    }

    for candidate in candidates:
        normalized_candidate = _clean_header(candidate)

        if normalized_candidate in normalized_columns:
            return normalized_columns[normalized_candidate]

    for candidate in candidates:
        normalized_candidate = _clean_header(candidate)

        if len(normalized_candidate) < 8:
            continue

        matches = [
            original
            for normalized, original in normalized_columns.items()
            if normalized.startswith(normalized_candidate)
            or normalized_candidate.startswith(normalized)
        ]

        if len(matches) == 1:
            return matches[0]

    return None


def normalize_identifier(
    value: object,
    append_00_to_9_digits: bool = False,
) -> str:
    """Normalize group and member identifiers read from Excel."""
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if re.fullmatch(r"\d+\.0+", text):
        text = text.split(".", 1)[0]

    digits = re.sub(r"\D", "", text)

    if append_00_to_9_digits and len(digits) == 9:
        digits += "00"

    return digits


def _clean_name(value: object) -> str:
    """Return a clean member name or an empty string."""
    if pd.isna(value):
        return ""

    text = re.sub(r"\s+", " ", str(value).strip())

    if text.lower() in {
        "",
        "nan",
        "none",
        "null",
        "(blank)",
        "blank",
    }:
        return ""

    return text


def _read_data_sheet(uploaded_file: BinaryIO) -> pd.DataFrame:
    """Read the worksheet named data from an uploaded workbook."""
    raw = (
        uploaded_file.getvalue()
        if hasattr(uploaded_file, "getvalue")
        else uploaded_file.read()
    )

    excel = pd.ExcelFile(io.BytesIO(raw))

    sheet = next(
        (
            sheet_name
            for sheet_name in excel.sheet_names
            if sheet_name.strip().lower() == "data"
        ),
        None,
    )

    if sheet is None:
        raise ValueError(
            f"{uploaded_file.name}: no sheet named 'data'. "
            f"Available sheets: {', '.join(excel.sheet_names)}"
        )

    return pd.read_excel(
        excel,
        sheet_name=sheet,
    )


def infer_benefit_type(filename, columns) -> str:
    """
    Detect the claim benefit from the filename and column names.

    Dental is standardized as DENT.
    """
    name = Path(filename).stem.upper()
    joined = " ".join(str(column).upper() for column in columns)

    if (
        "DENTAL" in name
        or re.search(r"(^|[^A-Z])DENT([^A-Z]|$)", name)
        or "DENTAL" in joined
    ):
        return "DENT"

    if (
        "VISION" in name
        or re.search(r"(^|[^A-Z])VIS([^A-Z]|$)", name)
        or "VISION" in joined
    ):
        return "VISION"

    if (
        re.search(r"(^|[^A-Z])RX([^A-Z]|$)", name)
        or "PRESCRIPTION" in name
        or "PHARM" in name
        or "DRUG NAME" in joined
        or "PRESCRIPTION" in joined
        or "PHARM" in joined
    ):
        return "RX"

    return "MED"


def read_claim_file(uploaded_file) -> pd.DataFrame:
    """Read and standardize one claim workbook."""
    df = _read_data_sheet(uploaded_file)

    if df.empty:
        raise ValueError(
            f"{uploaded_file.name}: the data sheet is empty."
        )

    columns = list(df.columns)

    group_col = _find_column(
        columns,
        GROUP_CANDIDATES,
    )
    member_col = _find_column(
        columns,
        MEMBER_CANDIDATES,
    )
    amount_col = _find_column(
        columns,
        AMOUNT_CANDIDATES,
    )
    first_col = _find_column(
        columns,
        FIRST_NAME_CANDIDATES,
    )
    last_col = _find_column(
        columns,
        LAST_NAME_CANDIDATES,
    )

    missing = [
        label
        for label, column in [
            ("Group Number", group_col),
            ("Member ID", member_col),
            ("Claim Amount", amount_col),
        ]
        if column is None
    ]

    if missing:
        raise ValueError(
            f"{uploaded_file.name}: could not detect "
            f"{', '.join(missing)}. "
            f"Columns found: {', '.join(map(str, columns))}"
        )

    output = pd.DataFrame(index=df.index)

    output["Group Number"] = df[group_col].map(
        normalize_identifier
    )

    output["Member ID"] = df[member_col].map(
        lambda value: normalize_identifier(
            value,
            append_00_to_9_digits=True,
        )
    )

    output["First Name"] = (
        df[first_col].map(_clean_name)
        if first_col is not None
        else ""
    )

    output["Last Name"] = (
        df[last_col].map(_clean_name)
        if last_col is not None
        else ""
    )

    output["Benefit"] = infer_benefit_type(
        uploaded_file.name,
        columns,
    )

    output["Claim Amount"] = pd.to_numeric(
        df[amount_col],
        errors="coerce",
    ).fillna(0.0)

    output["Source File"] = uploaded_file.name

    output = output[
        (output["Group Number"] != "")
        & (output["Member ID"] != "")
        & (output["Claim Amount"] != 0)
    ].copy()

    if output.empty:
        raise ValueError(
            f"{uploaded_file.name}: no usable claim rows remained "
            "after cleaning."
        )

    return output.reset_index(drop=True)


def read_all_claim_files(uploaded_files) -> pd.DataFrame:
    """
    Read all uploaded claim workbooks.

    Multiple companies and Group Numbers are allowed. app.py separates them
    and analyzes each group independently.
    """
    if not uploaded_files:
        raise ValueError(
            "Upload at least one claim workbook."
        )

    combined = pd.concat(
        [
            read_claim_file(uploaded_file)
            for uploaded_file in uploaded_files
        ],
        ignore_index=True,
    )

    if combined.empty:
        raise ValueError(
            "No usable claim rows were found in the uploaded files."
        )

    return combined
