from __future__ import annotations

from typing import Any

import pandas as pd


BENEFIT_ALIASES = {
    "MEDICAL": "MED",
    "MED": "MED",
    "PRESCRIPTION": "RX",
    "PHARMACY": "RX",
    "RX": "RX",
    "DENTAL": "DENT",
    "DENT": "DENT",
    "VISION": "VISION",
    "VIS": "VISION",
}


def _normalize_benefit(value: object) -> str:
    """Keep benefit names consistent across the analyzer."""
    if pd.isna(value):
        return ""

    text = str(value).strip().upper()
    return BENEFIT_ALIASES.get(text, text)


def _normalize_member_id(value: object) -> str:
    """Avoid member IDs such as 12345678900.0 after Excel imports."""
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if text.endswith(".0"):
        text = text[:-2]

    return text


def consolidate_claims(raw_claims: pd.DataFrame) -> pd.DataFrame:
    """
    Consolidate claims by Group Number and Member ID.

    This function supports data containing one or several groups. The new
    app.py normally sends one group at a time, but retaining Group Number
    in the grouping prevents claims from different companies from mixing.
    """
    required_columns = {
        "Group Number",
        "Member ID",
        "First Name",
        "Last Name",
        "Benefit",
        "Claim Amount",
    }

    missing_columns = required_columns - set(raw_claims.columns)

    if missing_columns:
        raise ValueError(
            "Claims data is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    claims = raw_claims.copy()

    claims["Group Number"] = (
        claims["Group Number"]
        .astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )

    claims["Member ID"] = claims[
        "Member ID"
    ].apply(_normalize_member_id)

    claims["Benefit"] = claims[
        "Benefit"
    ].apply(_normalize_benefit)

    claims["Claim Amount"] = pd.to_numeric(
        claims["Claim Amount"],
        errors="coerce",
    ).fillna(0.0)

    claims = claims[
        (claims["Group Number"] != "")
        & (claims["Member ID"] != "")
        & (claims["Benefit"] != "")
    ].copy()

    if claims.empty:
        raise ValueError(
            "No usable claims remained after consolidation cleaning."
        )

    names = (
        claims.groupby(
            ["Group Number", "Member ID"],
            as_index=False,
        )
        .agg(
            {
                "First Name": "first",
                "Last Name": "first",
            }
        )
    )

    totals = (
        claims.pivot_table(
            index=["Group Number", "Member ID"],
            columns="Benefit",
            values="Claim Amount",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
    )

    totals.columns.name = None

    result = names.merge(
        totals,
        on=["Group Number", "Member ID"],
        how="outer",
    )

    standard_benefits = [
        "MED",
        "RX",
        "DENT",
        "VISION",
    ]

    for benefit in standard_benefits:
        if benefit not in result.columns:
            result[benefit] = 0.0

    identification_columns = {
        "Group Number",
        "Member ID",
        "First Name",
        "Last Name",
    }

    benefit_columns = [
        column
        for column in result.columns
        if column not in identification_columns
    ]

    for column in benefit_columns:
        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        ).fillna(0.0)

    result["Total Claims"] = result[
        benefit_columns
    ].sum(axis=1)

    preferred_order = [
        "Group Number",
        "Member ID",
        "First Name",
        "Last Name",
        "MED",
        "RX",
        "DENT",
        "VISION",
    ]

    other_benefits = [
        column
        for column in benefit_columns
        if column not in standard_benefits
    ]

    result = result[
        preferred_order
        + other_benefits
        + ["Total Claims"]
    ]

    return (
        result.sort_values(
            "Total Claims",
            ascending=False,
        )
        .reset_index(drop=True)
    )


def apply_contract_rules(
    consolidated: pd.DataFrame,
    contract: dict[str, Any],
    alternative_deductible: float | None = None,
    replace_lasers: bool = False,
) -> pd.DataFrame:
    """
    Apply one contract to one consolidated group.

    The app.py separates groups before calling this function, preventing
    one company's deductible or laser rules from being applied to another.
    """
    if consolidated.empty:
        raise ValueError(
            "There are no consolidated claims to analyze."
        )

    contract_group = str(
        contract.get("group_number", "")
    ).strip()

    if contract_group.endswith(".0"):
        contract_group = contract_group[:-2]

    claim_groups = (
        consolidated["Group Number"]
        .astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .dropna()
        .unique()
        .tolist()
    )

    if len(claim_groups) != 1:
        raise ValueError(
            "Contract rules must be applied to one Group Number at a time. "
            f"Detected: {', '.join(sorted(claim_groups))}"
        )

    if contract_group and claim_groups[0] != contract_group:
        raise ValueError(
            f"The contract is for Group {contract_group}, but the claims "
            f"belong to Group {claim_groups[0]}."
        )

    deductible = contract.get("deductible")
    maximum = contract.get("maximum_liability")

    if deductible is None and alternative_deductible is None:
        raise ValueError(
            "The contract deductible is missing. "
            "Enter an Alternative Deductible."
        )

    if maximum is None:
        raise ValueError(
            "The contract maximum liability is missing in contracts.py."
        )

    standard = (
        float(alternative_deductible)
        if alternative_deductible is not None
        else float(deductible)
    )

    maximum = float(maximum)
    member_rules = contract.get("member_rules", {})

    rows = []

    for _, row in consolidated.iterrows():

        item = row.to_dict()

        member = _normalize_member_id(
            item["Member ID"]
        )

        total = float(
            item["Total Claims"]
        )

        rule = member_rules.get(
            member,
            {"type": "standard"},
        )

        rule_type = str(
            rule.get("type", "standard")
        ).lower()

        contract_laser = None

        if rule_type == "excluded":

            applicable = None
            status = "Excluded - No Coverage"
            liability = 0.0
            above = 0.0

        else:

            if rule_type == "laser":

                contract_laser = float(
                    rule["deductible"]
                )

                applicable = (
                    standard
                    if replace_lasers
                    else contract_laser
                )

                status = "Laser"

            else:

                applicable = standard
                status = "Standard"

            excess = max(
                total - float(applicable),
                0.0,
            )

            liability = min(
                excess,
                maximum,
            )

            above = max(
                excess - maximum,
                0.0,
            )

        if (
            alternative_deductible is not None
            and replace_lasers
        ):
            analysis_mode = (
                "Alternative deductible replaces all deductibles"
            )

        elif alternative_deductible is not None:
            analysis_mode = (
                "Alternative deductible; contract lasers retained"
            )

        else:
            analysis_mode = "Contract terms"

        item.update(
            {
                "Rule Type": rule_type.title(),
                "Contract Laser": contract_laser,
                "Applicable Deductible": applicable,
                "Coverage Status": status,
                "Maximum Redbridge Liability": maximum,
                "Redbridge Liability": liability,
                "Above Coverage Limit": above,
                "Exceeds Deductible": liability > 0,
                "Policy Year": contract["policy_year"],
                "Company": contract["company"],
                "Analysis Deductible": standard,
                "Analysis Mode": analysis_mode,
            }
        )

        rows.append(item)

    return (
        pd.DataFrame(rows)
        .sort_values(
            "Total Claims",
            ascending=False,
        )
        .reset_index(drop=True)
    )
