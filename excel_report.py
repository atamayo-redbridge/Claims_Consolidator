from io import BytesIO
import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

MONEY_COLUMNS = {"MED", "RX", "DENTAL", "VISION", "Total Claims", "Contract Laser", "Applicable Deductible", "Maximum Redbridge Liability", "Redbridge Liability", "Above Coverage Limit", "Analysis Deductible"}

def build_excel_report(analysis, raw_claims, contract):
    lasers, excluded = [], []
    for member, rule in contract.get("member_rules", {}).items():
        if rule.get("type") == "laser": lasers.append(f"{member}: ${rule['deductible']:,.2f}")
        if rule.get("type") == "excluded": excluded.append(member)
    summary = pd.DataFrame([
        ("Company", contract.get("company", "")), ("Group Number", contract.get("group_number", "")), ("Policy Year", contract.get("policy_year", "")),
        ("Contract Deductible", contract.get("deductible")), ("Analysis Deductible", analysis["Analysis Deductible"].iloc[0] if not analysis.empty else None),
        ("Maximum Redbridge Liability", contract.get("maximum_liability")), ("Covered Benefits", ", ".join(contract.get("covered_benefits", []))),
        ("Analysis Mode", analysis["Analysis Mode"].iloc[0] if not analysis.empty else ""), ("Laser Members", "\n".join(lasers) if lasers else "None"),
        ("Excluded Members", "\n".join(excluded) if excluded else "None"), ("Notes", contract.get("notes", ""))], columns=["Field", "Value"])
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Summary", index=False)
        analysis[analysis["Redbridge Liability"] > 0].to_excel(writer, sheet_name="Large Claims", index=False)
        analysis.to_excel(writer, sheet_name="All Members", index=False)
        analysis[analysis["Coverage Status"] == "Excluded - No Coverage"].to_excel(writer, sheet_name="Excluded Members", index=False)
        raw_claims.to_excel(writer, sheet_name="Raw Claims", index=False)
        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions
            for cell in ws[1]:
                cell.font = Font(color="FFFFFF", bold=True); cell.fill = PatternFill("solid", fgColor="1F4E78"); cell.alignment = Alignment(horizontal="center")
            headers = {cell.value: cell.column for cell in ws[1]}
            for col in MONEY_COLUMNS:
                if col in headers:
                    for r in range(2, ws.max_row + 1): ws.cell(r, headers[col]).number_format = '$#,##0.00'
            for cells in ws.columns:
                letter = get_column_letter(cells[0].column); width = min(max(len(str(c.value)) if c.value is not None else 0 for c in cells) + 2, 40); ws.column_dimensions[letter].width = max(width, 12)
    return output.getvalue()
