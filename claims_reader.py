from __future__ import annotations

import io
import re
from pathlib import Path
from typing import BinaryIO

import pandas as pd


GROUP_CANDIDATES = [
    "GROUP NUMBER",
    "GRPNUM",
    "GROUP",
    "GROUP NO",
    "GROUP #",
    "COMPNO",
    "COMP NO",
    "COMPANY NUMBER",
]

MEMBER_CANDIDATES = [
    "MEMBER ID NUMBER",
    "MEMBER ID",
    "MEMBERID",
    "MEMBNO",
    "MEMBER NUMBER",
    "MEMBER NO",
    "CERTIFICATE NUMBER",
]

AMOUNT_CANDIDATES = [
    "AMOUNT PAID",
    "PAID AMOUNT",
    "COMPUTED",
    "CLAIM AMOUNT",
    "NET PAID",
    "TOTAL PAID",
    "AMOUNT",
    "PAID",
]

FIRST_NAME_CANDIDATES = [
    "MEMB FIRST NAME",
    "MEMBER FIRST NAME",
    "FIRST NAME",
    "FSTNAM",
    "FIRST",
]

LAST_NAME_CANDIDATES = [
    "MEMB LAS NAME",
    "MEMB LAST NAME",
    "MEMBER LAST NAME",
    "LAST NAME",
    "LSTNAM",
    "LAST",
]


def _clean(value):
    return re.sub(r"\s+", " ", str(value).strip().upper())


def _find(columns, candidates):
    normalized = {_clean(column): column for column in columns}

    for candidate in candidates:
        normalized_candidate = _clean(candidate)

        if normalized_candidate in normalized:
            return normalized[normalized_candidate]

    for normalized_column, original_column in normalized.items():
        for candidate in candidates:
            normalized_candidate = _clean(candidate)

            if (
                normalized_candidate in normalized_column
                or normalized_column in normalized_candidate
            ):
                return original_column

    return None


def normalize_identifier(value, append_00_to_9_digits=False):
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if re.fullmatch(r"\d+\.0+", text):
        text = text.split(".")[0]

    digits = re.sub(r"\D", "", text)

    if append_00_to_9_digits and len(digits) == 9:
        digits += "00"

    return digits


def _read_data_sheet(uploaded_file: BinaryIO):
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
            f"Available: {', '.join(excel.sheet_names)}"
        )

    return pd.read_excel(
        excel,
        sheet_name=sheet,
    )


def infer_benefit_type(filename, columns):
    """
    Detect the claim benefit from the file name or column names.

    Dental is standardized as DENT because that is how the source
    workbooks are named and how the analyzer will identify it.
    """
    name = Path(filename).stem.upper()
    joined = " ".join(_clean(column) for column in columns)

    if (
        "DENTAL" in name
        or re.search(r"(^|[^A-Z])DENT([^A-Z]|$)", name)
        or "DENTAL" in joined
        or re.search(r"(^|[^A-Z])DENT([^A-Z]|$)", joined)
    ):
        return "DENT"

    if "VISION" in name or "VISION" in joined:
        return "VISION"

    if (
        re.search(r"(^|[^A-Z])RX([^A-Z]|$)", name)
        or "PRESCRIPTION" in joined
        or "PHARM" in name
        or "PHARM" in joined
    ):
        return "RX"

    return "MED"


def read_claim_file(uploaded_file):
    df = _read_data_sheet(uploaded_file)

    if df.empty:
        raise ValueError(
            f"{uploaded_file.name}: the data sheet is empty."
        )

    columns = list(df.columns)

    group_col = _find(
        columns,
        GROUP_CANDIDATES,
    )

    member_col = _find(
        columns,
        MEMBER_CANDIDATES,
    )

    amount_col = _find(
        columns,
        AMOUNT_CANDIDATES,
    )

    first_col = _find(
        columns,
        FIRST_NAME_CANDIDATES,
    )

    last_col = _find(
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
        if not column
    ]

    if missing:
        raise ValueError(
            f"{uploaded_file.name}: could not detect "
            f"{', '.join(missing)}. "
            f"Columns: {', '.join(map(str, columns))}"
        )

    output = pd.DataFrame()

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
        df[first_col]
        .fillna("")
        .astype(str)
        .str.strip()
        if first_col
        else ""
    )

    output["Last Name"] = (
        df[last_col]
        .fillna("")
        .astype(str)
        .str.strip()
        if last_col
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
            f"{uploaded_file.name}: no usable claim rows "
            "remained after cleaning."
        )

    return output


def read_all_claim_files(uploaded_files):
    """
    Read all uploaded claim workbooks.

    Multiple Group Numbers are allowed. The app.py file is responsible
    for separating and analyzing each group independently.
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
