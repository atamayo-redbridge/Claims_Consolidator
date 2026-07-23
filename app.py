import io
import re

import pandas as pd
import streamlit as st


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Redbridge Claims Consolidator",
    page_icon="📊",
    layout="wide",
)

st.title("Redbridge Claims Consolidator")

st.write(
    "Upload the RX and Vision claims reports to consolidate "
    "the claim amounts by policy number."
)

with st.expander("Expected Excel structure"):
    st.write(
        """
        - Row 3 contains the pivot table headers.
        - Column A contains the Policy Number.
        - Column B contains the Member First Name.
        - Column C contains the Claim Amount.
        - The actual data begins on row 4.
        """
    )


# ---------------------------------------------------------
# DATA CLEANING FUNCTIONS
# ---------------------------------------------------------

def clean_policy_number(value):
    """
    Clean policy numbers imported from Excel.

    Example:
    100245.0 becomes 100245.
    """

    if pd.isna(value):
        return ""

    policy_number = str(value).strip()

    policy_number = re.sub(
        r"\.0$",
        "",
        policy_number,
    )

    return policy_number


def clean_amount(amount_series):
    """
    Convert claim amounts to numeric values.

    Handles values such as:
    $1,250.00
    (500.00)
    300
    """

    cleaned_amount = (
        amount_series
        .astype(str)
        .str.strip()
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("(", "-", regex=False)
        .str.replace(")", "", regex=False)
    )

    return pd.to_numeric(
        cleaned_amount,
        errors="coerce",
    ).fillna(0.0)


# ---------------------------------------------------------
# READ CLAIMS FILE
# ---------------------------------------------------------

def read_claims_file(
    uploaded_file,
    claims_column_name,
):
    """
    Read a claims pivot-table report.

    Expected structure:
    Row 3 = headers
    Column A = Policy Number
    Column B = Member First Name
    Column C = Claim Amount
    """

    dataframe = pd.read_excel(
        uploaded_file,
        sheet_name=0,
        header=2,
        usecols="A:C",
    )

    if dataframe.shape[1] < 3:
        raise ValueError(
            "The file does not contain columns A, B, and C."
        )

    dataframe = dataframe.iloc[:, :3].copy()

    dataframe.columns = [
        "Policy Number",
        "Member First Name",
        claims_column_name,
    ]

    dataframe["Policy Number"] = dataframe[
        "Policy Number"
    ].map(clean_policy_number)

    dataframe[claims_column_name] = clean_amount(
        dataframe[claims_column_name]
    )

    invalid_policy_values = {
        "",
        "nan",
        "none",
        "grand total",
        "total",
        "(blank)",
    }

    dataframe = dataframe[
        ~dataframe["Policy Number"]
        .str.lower()
        .isin(invalid_policy_values)
    ].copy()

    grouped_dataframe = (
        dataframe
        .groupby(
            "Policy Number",
            as_index=False,
        )[claims_column_name]
        .sum()
    )

    return grouped_dataframe


# ---------------------------------------------------------
# CLASSIFY POLICIES
# ---------------------------------------------------------

def classify_policy_source(row):
    """
    Identify whether a policy exists in RX, Vision, or both.
    """

    has_rx = row["RX Claims"] != 0
    has_vision = row["Vision Claims"] != 0

    if has_rx and has_vision:
        return "RX and Vision"

    if has_rx:
        return "RX Only"

    if has_vision:
        return "Vision Only"

    return "Zero Amount"


# ---------------------------------------------------------
# CREATE DOWNLOADABLE EXCEL REPORT
# ---------------------------------------------------------

def create_excel_report(
    consolidated,
    company_summary,
    exceptions,
):
    """
    Create an Excel workbook with three worksheets:
    Claims Detail, Company Summary, and Exceptions.
    """

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        consolidated.to_excel(
            writer,
            sheet_name="Claims Detail",
            index=False,
        )

        company_summary.to_excel(
            writer,
            sheet_name="Company Summary",
            index=False,
        )

        exceptions.to_excel(
            writer,
            sheet_name="Exceptions",
            index=False,
        )

        workbook = writer.book

        for sheet_name in workbook.sheetnames:
            worksheet = workbook[sheet_name]

            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions

            for column_cells in worksheet.columns:
                maximum_length = 0

                for cell in column_cells:
                    cell_value = (
                        ""
                        if cell.value is None
                        else str(cell.value)
                    )

                    maximum_length = max(
                        maximum_length,
                        len(cell_value),
                    )

                column_letter = column_cells[
                    0
                ].column_letter

                worksheet.column_dimensions[
                    column_letter
                ].width = min(
                    maximum_length + 3,
                    40,
                )

        detail_sheet = workbook[
            "Claims Detail"
        ]

        detail_headers = {
            cell.value: cell.column
            for cell in detail_sheet[1]
        }

        for column_name in [
            "RX Claims",
            "Vision Claims",
            "Total Claims",
        ]:
            column_number = detail_headers.get(
                column_name
            )

            if column_number:
                for row_number in range(
                    2,
                    detail_sheet.max_row + 1,
                ):
                    detail_sheet.cell(
                        row=row_number,
                        column=column_number,
                    ).number_format = "$#,##0.00"

        summary_sheet = workbook[
            "Company Summary"
        ]

        summary_headers = {
            cell.value: cell.column
            for cell in summary_sheet[1]
        }

        for column_name in [
            "Total RX Claims",
            "Total Vision Claims",
            "Total Claims",
        ]:
            column_number = summary_headers.get(
                column_name
            )

            if column_number:
                for row_number in range(
                    2,
                    summary_sheet.max_row + 1,
                ):
                    summary_sheet.cell(
                        row=row_number,
                        column=column_number,
                    ).number_format = "$#,##0.00"

    output.seek(0)

    return output.getvalue()


# ---------------------------------------------------------
# USER INPUTS
# ---------------------------------------------------------

company_name = st.text_input(
    "Company name",
    placeholder="Example: Healthcare International",
)

left_column, right_column = st.columns(2)

with left_column:
    rx_file = st.file_uploader(
        "Upload RX claims report",
        type=["xlsx", "xls"],
        key="rx_file",
    )

with right_column:
    vision_file = st.file_uploader(
        "Upload Vision claims report",
        type=["xlsx", "xls"],
        key="vision_file",
    )

process_button = st.button(
    "Process Claims",
    type="primary",
    use_container_width=True,
)


# ---------------------------------------------------------
# PROCESS FILES
# ---------------------------------------------------------

if process_button:

    if rx_file is None and vision_file is None:
        st.error(
            "Please upload at least one RX or Vision report."
        )

        st.stop()

    try:

        rx_data = pd.DataFrame(
            columns=[
                "Policy Number",
                "RX Claims",
            ]
        )

        vision_data = pd.DataFrame(
            columns=[
                "Policy Number",
                "Vision Claims",
            ]
        )

        if rx_file is not None:
            rx_data = read_claims_file(
                rx_file,
                "RX Claims",
            )

        if vision_file is not None:
            vision_data = read_claims_file(
                vision_file,
                "Vision Claims",
            )

        consolidated = pd.merge(
            rx_data,
            vision_data,
            on="Policy Number",
            how="outer",
        )

        consolidated["RX Claims"] = consolidated[
            "RX Claims"
        ].fillna(0.0)

        consolidated[
            "Vision Claims"
        ] = consolidated[
            "Vision Claims"
        ].fillna(0.0)

        consolidated["Total Claims"] = (
            consolidated["RX Claims"]
            + consolidated["Vision Claims"]
        )

        consolidated[
            "Source Status"
        ] = consolidated.apply(
            classify_policy_source,
            axis=1,
        )

        final_company_name = (
            company_name.strip()
            if company_name.strip()
            else "Not specified"
        )

        consolidated.insert(
            0,
            "Company",
            final_company_name,
        )

        consolidated = consolidated[
            [
                "Company",
                "Policy Number",
                "RX Claims",
                "Vision Claims",
                "Total Claims",
                "Source Status",
            ]
        ]

        consolidated = consolidated.sort_values(
            by="Policy Number",
        ).reset_index(
            drop=True
        )

        total_rx = consolidated[
            "RX Claims"
        ].sum()

        total_vision = consolidated[
            "Vision Claims"
        ].sum()

        total_claims = consolidated[
            "Total Claims"
        ].sum()

        total_policies = len(
            consolidated
        )

        policies_in_both = (
            consolidated["Source Status"]
            == "RX and Vision"
        ).sum()

        rx_only = (
            consolidated["Source Status"]
            == "RX Only"
        ).sum()

        vision_only = (
            consolidated["Source Status"]
            == "Vision Only"
        ).sum()

        metric_1, metric_2, metric_3, metric_4 = st.columns(
            4
        )

        metric_1.metric(
            "Unique Policies",
            f"{total_policies:,}",
        )

        metric_2.metric(
            "RX Claims",
            f"${total_rx:,.2f}",
        )

        metric_3.metric(
            "Vision Claims",
            f"${total_vision:,.2f}",
        )

        metric_4.metric(
            "Total Claims",
            f"${total_claims:,.2f}",
        )

        st.subheader(
            "Consolidated Claims"
        )

        st.dataframe(
            consolidated,
            use_container_width=True,
            hide_index=True,
            column_config={
                "RX Claims": (
                    st.column_config.NumberColumn(
                        format="$%.2f"
                    )
                ),
                "Vision Claims": (
                    st.column_config.NumberColumn(
                        format="$%.2f"
                    )
                ),
                "Total Claims": (
                    st.column_config.NumberColumn(
                        format="$%.2f"
                    )
                ),
            },
        )

        exceptions = consolidated[
            consolidated[
                "Source Status"
            ].isin(
                [
                    "RX Only",
                    "Vision Only",
                ]
            )
        ].copy()

        st.subheader(
            "Policies Found in Only One Report"
        )

        if exceptions.empty:

            st.success(
                "Every policy appears in both reports."
            )

        else:

            st.dataframe(
                exceptions,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "RX Claims": (
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        )
                    ),
                    "Vision Claims": (
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        )
                    ),
                    "Total Claims": (
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        )
                    ),
                },
            )

        company_summary = pd.DataFrame(
            {
                "Company": [
                    final_company_name
                ],
                "Total RX Claims": [
                    total_rx
                ],
                "Total Vision Claims": [
                    total_vision
                ],
                "Total Claims": [
                    total_claims
                ],
                "Unique Policies": [
                    total_policies
                ],
                "Policies in Both": [
                    policies_in_both
                ],
                "RX Only": [
                    rx_only
                ],
                "Vision Only": [
                    vision_only
                ],
            }
        )

        excel_report = create_excel_report(
            consolidated,
            company_summary,
            exceptions,
        )

        safe_company_name = re.sub(
            r"[^A-Za-z0-9_-]+",
            "_",
            final_company_name,
        ).strip("_")

        if not safe_company_name:
            safe_company_name = "company"

        st.download_button(
            label="Download Consolidated Excel",
            data=excel_report,
            file_name=(
                f"{safe_company_name}_"
                f"claims_consolidated.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True,
        )

    except Exception as error:

        st.error(
            "The reports could not be processed."
        )

        st.exception(
            error
        )




