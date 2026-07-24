import io
import re

import pandas as pd
import streamlit as st
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Claims Excess Analyzer",
    page_icon="📊",
    layout="wide",
)

st.title("Claims Excess Analyzer")

st.write(
    """
    Upload two claims reports, select the claim type for each file,
    consolidate the amounts by Group Number and Member ID, and identify
    members whose combined claims exceed the selected deductible.
    """
)


# =========================================================
# GENERAL FUNCTIONS
# =========================================================

def find_data_sheet(uploaded_file):
    """
    Locate the worksheet named 'data'.

    Spaces and capitalization are ignored.
    """

    excel_file = pd.ExcelFile(uploaded_file)

    for sheet_name in excel_file.sheet_names:
        if sheet_name.strip().lower() == "data":
            return sheet_name

    raise ValueError(
        f"The file '{uploaded_file.name}' does not contain "
        "a worksheet named 'data'."
    )


def clean_text(value):
    """
    Convert a value imported from Excel into clean text.
    """

    if pd.isna(value):
        return ""

    value = str(value).strip()

    return re.sub(
        r"\.0$",
        "",
        value,
    )


def normalize_member_id(value):
    """
    Standardize Member IDs to 11 digits.

    A 9-digit Member ID receives two zeros at the end.

    Example:
    234045521 becomes 23404552100

    An 11-digit Member ID remains unchanged.
    """

    member_id = clean_text(value)

    # Keep numbers only.
    member_id = re.sub(
        r"\D",
        "",
        member_id,
    )

    if len(member_id) == 9:
        member_id = member_id + "00"

    return member_id


def normalize_group_number(value):
    """
    Standardize the Group Number as text.
    """

    group_number = clean_text(value)

    return re.sub(
        r"\D",
        "",
        group_number,
    )


def clean_amount(series):
    """
    Convert claim amounts to numbers.

    Handles formats such as:
    $1,250.00
    1,250.00
    (500.00)
    """

    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("(", "-", regex=False)
        .str.replace(")", "", regex=False)
    )

    return pd.to_numeric(
        cleaned,
        errors="coerce",
    ).fillna(0.0)


def normalize_column_name(column_name):
    """
    Standardize column names to make detection easier.
    """

    column_name = str(column_name).strip().lower()

    column_name = re.sub(
        r"[^a-z0-9]+",
        " ",
        column_name,
    )

    return " ".join(
        column_name.split()
    )


def find_column(dataframe, possible_names):
    """
    Find a column using several possible names.
    """

    normalized_columns = {
        normalize_column_name(column): column
        for column in dataframe.columns
    }

    normalized_options = [
        normalize_column_name(name)
        for name in possible_names
    ]

    # First, try exact matches.
    for option in normalized_options:
        if option in normalized_columns:
            return normalized_columns[option]

    # Then try partial matches.
    for option in normalized_options:
        for normalized_column, original_column in normalized_columns.items():
            if option in normalized_column:
                return original_column

    return None


# =========================================================
# COLUMN DETECTION
# =========================================================

def detect_columns(dataframe):
    """
    Automatically detect the main columns inside the data worksheet.
    """

    group_column = find_column(
        dataframe,
        [
            "group number",
            "group no",
            "group num",
            "grpnum",
            "group",
        ],
    )

    member_column = find_column(
        dataframe,
        [
            "member id number",
            "member id",
            "member number",
            "member no",
            "membno",
            "row labels",
        ],
    )

    first_name_column = find_column(
        dataframe,
        [
            "member first name",
            "memb first name",
            "first name",
            "fstnam",
        ],
    )

    last_name_column = find_column(
        dataframe,
        [
            "member last name",
            "memb last name",
            "memb las name",
            "last name",
            "lstnam",
        ],
    )

    amount_column = find_column(
        dataframe,
        [
            "amount paid",
            "claim amount",
            "paid amount",
            "computed",
            "sum of amount paid",
            "sum of computed",
            "total paid",
        ],
    )

    missing = []

    if member_column is None:
        missing.append("Member ID")

    if amount_column is None:
        missing.append("Claim Amount")

    if missing:
        raise ValueError(
            "The following required columns could not be detected: "
            + ", ".join(missing)
            + ". Available columns: "
            + ", ".join(
                str(column)
                for column in dataframe.columns
            )
        )

    return {
        "group": group_column,
        "member": member_column,
        "first_name": first_name_column,
        "last_name": last_name_column,
        "amount": amount_column,
    }


# =========================================================
# READ A GENERIC CLAIMS FILE
# =========================================================

def read_claims_file(
    uploaded_file,
    claim_type,
):
    """
    Read any MED, RX, Dental, Vision, or other claims file.

    The program reads the worksheet called 'data' and automatically
    identifies the Group Number, Member ID, member names, and amount.
    """

    sheet_name = find_data_sheet(
        uploaded_file
    )

    dataframe = pd.read_excel(
        uploaded_file,
        sheet_name=sheet_name,
    )

    # Remove completely empty rows and columns.
    dataframe = dataframe.dropna(
        how="all"
    )

    dataframe = dataframe.dropna(
        axis=1,
        how="all",
    )

    columns = detect_columns(
        dataframe
    )

    result = pd.DataFrame()

    if columns["group"] is not None:
        result["Group Number"] = dataframe[
            columns["group"]
        ].map(normalize_group_number)
    else:
        result["Group Number"] = ""

    result["Member ID"] = dataframe[
        columns["member"]
    ].map(normalize_member_id)

    if columns["first_name"] is not None:
        result["First Name"] = (
            dataframe[columns["first_name"]]
            .fillna("")
            .astype(str)
            .str.strip()
        )
    else:
        result["First Name"] = ""

    if columns["last_name"] is not None:
        result["Last Name"] = (
            dataframe[columns["last_name"]]
            .fillna("")
            .astype(str)
            .str.strip()
        )
    else:
        result["Last Name"] = ""

    claims_column_name = (
        f"{claim_type} Claims"
    )

    result[claims_column_name] = clean_amount(
        dataframe[columns["amount"]]
    )

    invalid_member_values = {
        "",
        "nan",
        "none",
        "grandtotal",
        "total",
        "blank",
    }

    normalized_member_values = (
        result["Member ID"]
        .astype(str)
        .str.lower()
        .str.replace(
            r"[^a-z0-9]",
            "",
            regex=True,
        )
    )

    result = result[
        ~normalized_member_values.isin(
            invalid_member_values
        )
    ].copy()

    group_columns = [
        "Group Number",
        "Member ID",
    ]

    result = (
        result.groupby(
            group_columns,
            as_index=False,
        )
        .agg(
            {
                "First Name": "first",
                "Last Name": "first",
                claims_column_name: "sum",
            }
        )
    )

    return result


# =========================================================
# COMBINE TWO CLAIM TYPES
# =========================================================

def combine_claims(
    file_1_data,
    file_2_data,
    claim_type_1,
    claim_type_2,
):
    """
    Combine two reports using Group Number and Member ID.
    """

    amount_column_1 = (
        f"{claim_type_1} Claims"
    )

    amount_column_2 = (
        f"{claim_type_2} Claims"
    )

    combined = pd.merge(
        file_1_data,
        file_2_data,
        on=[
            "Group Number",
            "Member ID",
        ],
        how="outer",
        suffixes=(
            " File 1",
            " File 2",
        ),
    )

    combined[amount_column_1] = combined[
        amount_column_1
    ].fillna(0.0)

    combined[amount_column_2] = combined[
        amount_column_2
    ].fillna(0.0)

    combined["First Name"] = combined[
        "First Name File 1"
    ].fillna(
        combined["First Name File 2"]
    )

    combined["Last Name"] = combined[
        "Last Name File 1"
    ].fillna(
        combined["Last Name File 2"]
    )

    combined["First Name"] = combined[
        "First Name"
    ].fillna("")

    combined["Last Name"] = combined[
        "Last Name"
    ].fillna("")

    combined["Total Claims"] = (
        combined[amount_column_1]
        + combined[amount_column_2]
    )

    combined = combined[
        [
            "Group Number",
            "Member ID",
            "First Name",
            "Last Name",
            amount_column_1,
            amount_column_2,
            "Total Claims",
        ]
    ]

    return combined


# =========================================================
# EXCEL REPORT
# =========================================================

def create_excel_report(
    excess_claims,
    all_claims,
    deductible,
    claim_type_1,
    claim_type_2,
):
    """
    Create the downloadable Excel report.
    """

    output = io.BytesIO()

    amount_column_1 = (
        f"{claim_type_1} Claims"
    )

    amount_column_2 = (
        f"{claim_type_2} Claims"
    )

    summary = pd.DataFrame(
        {
            "Claim Type 1": [
                claim_type_1
            ],
            "Claim Type 2": [
                claim_type_2
            ],
            "Selected Deductible": [
                deductible
            ],
            "Members Over Deductible": [
                len(excess_claims)
            ],
            f"Total {claim_type_1} Claims": [
                excess_claims[
                    amount_column_1
                ].sum()
            ],
            f"Total {claim_type_2} Claims": [
                excess_claims[
                    amount_column_2
                ].sum()
            ],
            "Total Combined Claims": [
                excess_claims[
                    "Total Claims"
                ].sum()
            ],
            "Total Excess Claims": [
                excess_claims[
                    "Excess Claims"
                ].sum()
            ],
        }
    )

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        excess_claims.to_excel(
            writer,
            sheet_name="Claims Over Deductible",
            index=False,
        )

        summary.to_excel(
            writer,
            sheet_name="Summary",
            index=False,
        )

        all_claims.to_excel(
            writer,
            sheet_name="All Members",
            index=False,
        )

        workbook = writer.book

        header_fill = PatternFill(
            fill_type="solid",
            fgColor="1F4E78",
        )

        header_font = Font(
            color="FFFFFF",
            bold=True,
        )

        for worksheet in workbook.worksheets:

            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = (
                worksheet.dimensions
            )

            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(
                    horizontal="center"
                )

            for column_cells in worksheet.columns:

                maximum_length = max(
                    len(str(cell.value))
                    if cell.value is not None
                    else 0
                    for cell in column_cells
                )

                column_letter = get_column_letter(
                    column_cells[0].column
                )

                worksheet.column_dimensions[
                    column_letter
                ].width = min(
                    maximum_length + 3,
                    40,
                )

            for cell in worksheet[1]:

                header_name = str(
                    cell.value
                )

                if (
                    "Claims" in header_name
                    or "Deductible" in header_name
                ):
                    for row_number in range(
                        2,
                        worksheet.max_row + 1,
                    ):
                        worksheet.cell(
                            row=row_number,
                            column=cell.column,
                        ).number_format = (
                            '$#,##0.00;[Red]-$#,##0.00'
                        )

    output.seek(0)

    return output.getvalue()


# =========================================================
# STREAMLIT INPUTS
# =========================================================

claim_type_options = [
    "MED",
    "RX",
    "Dental",
    "Vision",
    "Other",
]

file_column_1, file_column_2 = st.columns(
    2
)

with file_column_1:

    st.subheader("Claims File 1")

    claim_type_1 = st.selectbox(
        "Claim type for File 1",
        options=claim_type_options,
        index=0,
        key="claim_type_1",
    )

    file_1 = st.file_uploader(
        "Upload the first claims report",
        type=[
            "xlsx",
            "xls",
        ],
        key="file_1",
    )

with file_column_2:

    st.subheader("Claims File 2")

    claim_type_2 = st.selectbox(
        "Claim type for File 2",
        options=claim_type_options,
        index=1,
        key="claim_type_2",
    )

    file_2 = st.file_uploader(
        "Upload the second claims report",
        type=[
            "xlsx",
            "xls",
        ],
        key="file_2",
    )


deductible_options = list(
    range(
        10_000,
        510_000,
        10_000,
    )
)

deductible = st.selectbox(
    "Select deductible",
    options=deductible_options,
    index=9,
    format_func=lambda value: (
        f"${value:,.0f}"
    ),
)

process_button = st.button(
    "Process Claims",
    type="primary",
    use_container_width=True,
)


# =========================================================
# PROCESS CLAIMS
# =========================================================

if process_button:

    if file_1 is None or file_2 is None:
        st.error(
            "Please upload both claims reports."
        )
        st.stop()

    if claim_type_1 == claim_type_2:
        st.error(
            "Select two different claim types."
        )
        st.stop()

    try:

        with st.spinner(
            "Reading and consolidating claims..."
        ):

            file_1_data = read_claims_file(
                uploaded_file=file_1,
                claim_type=claim_type_1,
            )

            file_2_data = read_claims_file(
                uploaded_file=file_2,
                claim_type=claim_type_2,
            )

            all_claims = combine_claims(
                file_1_data=file_1_data,
                file_2_data=file_2_data,
                claim_type_1=claim_type_1,
                claim_type_2=claim_type_2,
            )

            all_claims = all_claims.sort_values(
                by="Total Claims",
                ascending=False,
            ).reset_index(
                drop=True
            )

            excess_claims = all_claims[
                all_claims["Total Claims"]
                > deductible
            ].copy()

            excess_claims["Deductible"] = (
                deductible
            )

            excess_claims["Excess Claims"] = (
                excess_claims["Total Claims"]
                - deductible
            )

        amount_column_1 = (
            f"{claim_type_1} Claims"
        )

        amount_column_2 = (
            f"{claim_type_2} Claims"
        )

        group_numbers = sorted(
            all_claims[
                "Group Number"
            ]
            .dropna()
            .astype(str)
            .loc[
                lambda series: series != ""
            ]
            .unique()
            .tolist()
        )

        if group_numbers:
            st.success(
                "Claims processed successfully. "
                "Group Number(s): "
                + ", ".join(group_numbers)
            )
        else:
            st.success(
                "Claims processed successfully."
            )

        metric_1, metric_2, metric_3, metric_4 = st.columns(
            4
        )

        metric_1.metric(
            "Members Over Deductible",
            f"{len(excess_claims):,}",
        )

        metric_2.metric(
            "Selected Deductible",
            f"${deductible:,.0f}",
        )

        metric_3.metric(
            "Combined Claims",
            (
                f"${excess_claims['Total Claims'].sum():,.2f}"
            ),
        )

        metric_4.metric(
            "Total Excess",
            (
                f"${excess_claims['Excess Claims'].sum():,.2f}"
            ),
        )

        st.subheader(
            "Claims Over Deductible"
        )

        if excess_claims.empty:

            st.warning(
                "No members have combined claims above "
                f"${deductible:,.0f}."
            )

        else:

            st.dataframe(
                excess_claims,
                use_container_width=True,
                hide_index=True,
                column_config={
                    amount_column_1: (
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        )
                    ),
                    amount_column_2: (
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        )
                    ),
                    "Total Claims": (
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        )
                    ),
                    "Deductible": (
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        )
                    ),
                    "Excess Claims": (
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        )
                    ),
                },
            )

        with st.expander(
            "View all consolidated members"
        ):

            st.dataframe(
                all_claims,
                use_container_width=True,
                hide_index=True,
                column_config={
                    amount_column_1: (
                        st.column_config.NumberColumn(
                            format="$%.2f"
                        )
                    ),
                    amount_column_2: (
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

        excel_report = create_excel_report(
            excess_claims=excess_claims,
            all_claims=all_claims,
            deductible=deductible,
            claim_type_1=claim_type_1,
            claim_type_2=claim_type_2,
        )

        group_filename = (
            group_numbers[0]
            if len(group_numbers) == 1
            else "multiple_groups"
        )

        st.download_button(
            label="Download Excess Claims Report",
            data=excel_report,
            file_name=(
                f"group_{group_filename}_"
                f"{claim_type_1}_{claim_type_2}_"
                f"over_{deductible}.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True,
        )

    except Exception as error:

        st.error(
            "The files could not be processed."
        )

        st.exception(
            error
        )



