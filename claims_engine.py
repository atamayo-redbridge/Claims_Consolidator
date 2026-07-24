from __future__ import annotations
from typing import Any
import pandas as pd

def consolidate_claims(raw_claims: pd.DataFrame) -> pd.DataFrame:
    names = raw_claims.groupby(["Group Number", "Member ID"], as_index=False).agg({"First Name": "first", "Last Name": "first"})
    totals = raw_claims.pivot_table(index=["Group Number", "Member ID"], columns="Benefit", values="Claim Amount", aggfunc="sum", fill_value=0.0).reset_index()
    totals.columns.name = None
    result = names.merge(totals, on=["Group Number", "Member ID"], how="outer")
    benefit_cols = [c for c in result.columns if c not in {"Group Number", "Member ID", "First Name", "Last Name"}]
    result["Total Claims"] = result[benefit_cols].sum(axis=1)
    return result.sort_values("Total Claims", ascending=False).reset_index(drop=True)

def apply_contract_rules(consolidated: pd.DataFrame, contract: dict[str, Any], alternative_deductible=None, replace_lasers=False) -> pd.DataFrame:
    deductible, maximum = contract.get("deductible"), contract.get("maximum_liability")
    if deductible is None and alternative_deductible is None:
        raise ValueError("The contract deductible is missing. Enter an Alternative Deductible.")
    if maximum is None:
        raise ValueError("The contract maximum liability is missing in contracts.py.")
    standard = float(alternative_deductible) if alternative_deductible is not None else float(deductible)
    rows = []
    for _, row in consolidated.iterrows():
        item = row.to_dict(); member = str(item["Member ID"]); total = float(item["Total Claims"])
        rule = contract.get("member_rules", {}).get(member, {"type": "standard"}); typ = rule.get("type", "standard").lower()
        contract_laser = None
        if typ == "excluded":
            applicable, status, liability, above = None, "Excluded - No Coverage", 0.0, 0.0
        else:
            if typ == "laser":
                contract_laser = float(rule["deductible"])
                applicable = standard if replace_lasers else contract_laser
                status = "Laser"
            else:
                applicable, status = standard, "Standard"
            excess = max(total - float(applicable), 0.0)
            liability = min(excess, float(maximum)); above = max(excess - float(maximum), 0.0)
        item.update({"Rule Type": typ.title(), "Contract Laser": contract_laser, "Applicable Deductible": applicable, "Coverage Status": status, "Maximum Redbridge Liability": float(maximum), "Redbridge Liability": liability, "Above Coverage Limit": above, "Exceeds Deductible": liability > 0, "Policy Year": contract["policy_year"], "Company": contract["company"], "Analysis Deductible": standard, "Analysis Mode": "Alternative deductible replaces all deductibles" if alternative_deductible is not None and replace_lasers else "Alternative deductible; contract lasers retained" if alternative_deductible is not None else "Contract terms"})
        rows.append(item)
    return pd.DataFrame(rows).sort_values("Total Claims", ascending=False).reset_index(drop=True)
