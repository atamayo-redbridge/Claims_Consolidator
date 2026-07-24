from __future__ import annotations
import io, re
from pathlib import Path
from typing import BinaryIO
import pandas as pd

GROUP_CANDIDATES = ["GROUP NUMBER", "GRPNUM", "GROUP", "GROUP NO", "GROUP #", "COMPNO", "COMP NO", "COMPANY NUMBER"]
MEMBER_CANDIDATES = ["MEMBER ID NUMBER", "MEMBER ID", "MEMBERID", "MEMBNO", "MEMBER NUMBER", "MEMBER NO", "CERTIFICATE NUMBER"]
AMOUNT_CANDIDATES = ["AMOUNT PAID", "PAID AMOUNT", "COMPUTED", "CLAIM AMOUNT", "NET PAID", "TOTAL PAID", "AMOUNT", "PAID"]
FIRST_NAME_CANDIDATES = ["MEMB FIRST NAME", "MEMBER FIRST NAME", "FIRST NAME", "FSTNAM", "FIRST"]
LAST_NAME_CANDIDATES = ["MEMB LAS NAME", "MEMB LAST NAME", "MEMBER LAST NAME", "LAST NAME", "LSTNAM", "LAST"]

def _clean(value):
    return re.sub(r"\s+", " ", str(value).strip().upper())

def _find(columns, candidates):
    normalized = {_clean(c): c for c in columns}
    for candidate in candidates:
        if _clean(candidate) in normalized:
            return normalized[_clean(candidate)]
    for norm, original in normalized.items():
        for candidate in candidates:
            c = _clean(candidate)
            if c in norm or norm in c:
                return original
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
    raw = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
    excel = pd.ExcelFile(io.BytesIO(raw))
    sheet = next((s for s in excel.sheet_names if s.strip().lower() == "data"), None)
    if sheet is None:
        raise ValueError(f"{uploaded_file.name}: no sheet named 'data'. Available: {', '.join(excel.sheet_names)}")
    return pd.read_excel(excel, sheet_name=sheet)

def infer_benefit_type(filename, columns):
    name = Path(filename).stem.upper()
    joined = " ".join(_clean(c) for c in columns)
    if "DENTAL" in name or "DENTAL" in joined: return "DENTAL"
    if "VISION" in name or "VISION" in joined: return "VISION"
    if re.search(r"(^|[^A-Z])RX([^A-Z]|$)", name) or "PRESCRIPTION" in joined or "PHARM" in name: return "RX"
    return "MED"

def read_claim_file(uploaded_file):
    df = _read_data_sheet(uploaded_file)
    if df.empty: raise ValueError(f"{uploaded_file.name}: the data sheet is empty.")
    cols = list(df.columns)
    group_col, member_col, amount_col = _find(cols, GROUP_CANDIDATES), _find(cols, MEMBER_CANDIDATES), _find(cols, AMOUNT_CANDIDATES)
    first_col, last_col = _find(cols, FIRST_NAME_CANDIDATES), _find(cols, LAST_NAME_CANDIDATES)
    missing = [label for label, col in [("Group Number", group_col), ("Member ID", member_col), ("Claim Amount", amount_col)] if not col]
    if missing: raise ValueError(f"{uploaded_file.name}: could not detect {', '.join(missing)}. Columns: {', '.join(map(str, cols))}")
    out = pd.DataFrame()
    out["Group Number"] = df[group_col].map(normalize_identifier)
    out["Member ID"] = df[member_col].map(lambda x: normalize_identifier(x, True))
    out["First Name"] = df[first_col].fillna("").astype(str).str.strip() if first_col else ""
    out["Last Name"] = df[last_col].fillna("").astype(str).str.strip() if last_col else ""
    out["Benefit"] = infer_benefit_type(uploaded_file.name, cols)
    out["Claim Amount"] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0.0)
    out["Source File"] = uploaded_file.name
    out = out[(out["Group Number"] != "") & (out["Member ID"] != "") & (out["Claim Amount"] != 0)].copy()
    if out.empty: raise ValueError(f"{uploaded_file.name}: no usable claim rows remained after cleaning.")
    return out

def read_all_claim_files(uploaded_files):
    if not uploaded_files: raise ValueError("Upload at least one claim workbook.")
    combined = pd.concat([read_claim_file(f) for f in uploaded_files], ignore_index=True)
    groups = sorted(combined["Group Number"].dropna().unique().tolist())
    if len(groups) != 1: raise ValueError(f"The uploaded files must contain exactly one Group Number. Detected: {', '.join(groups)}")
    return combined
