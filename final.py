import os
import pandas as pd
import streamlit as st

# Set Streamlit page configuration
st.set_page_config(
    page_title="📑 File Operations Tool",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ensure a temporary directory exists
TEMP_DIR = "temp_uploaded_files"
os.makedirs(TEMP_DIR, exist_ok=True)

# Cache data to improve speed
@st.cache_data(show_spinner=False)
def read_csv(file):
    """Read a CSV file."""
    try:
        return pd.read_csv(file, encoding="ISO-8859-1")
    except Exception as e:
        st.error(f"Error reading CSV file: {e}")
        return None

@st.cache_data(show_spinner=False)
def read_excel(file):
    """Read an Excel file and return sheet names."""
    try:
        excel_file = pd.ExcelFile(file, engine="openpyxl")
        return excel_file.sheet_names
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")
        return None

def load_excel_sheet(file, sheet_name):
    """Load a specific sheet from an Excel file."""
    try:
        return pd.read_excel(file, sheet_name=sheet_name, engine="openpyxl")
    except Exception as e:
        st.error(f"Error reading sheet '{sheet_name}': {e}")
        return None

@st.cache_data(show_spinner=False)
def validate_columns(dfs):
    """Check if all dataframes have identical columns."""
    columns_list = [set(df.columns) for df in dfs]
    return all(cols == columns_list[0] for cols in columns_list)

@st.cache_data(show_spinner=False)
def append_files(files, selected_sheets):
    """Append files while validating column consistency."""
    dfs = []
    for file in files:
        if file.name.endswith(("xlsx", "xls")):
            sheet_name = selected_sheets.get(file.name)
            if sheet_name:
                df = load_excel_sheet(file, sheet_name)
                if df is not None:
                    dfs.append(df)
        else:
            df = read_csv(file)
            if df is not None:
                dfs.append(df)

    if dfs and validate_columns(dfs):
        return pd.concat(dfs, ignore_index=True)
    else:
        st.error("Column mismatch detected. Ensure all files have the same structure.")
        return None

def preview_dataframe(df, n=5):
    """Preview the first few rows of a dataframe."""
    return df.head(n)

def summarize_csv_files(df, selected_operation, selected_columns, group_by_columns, include_all_columns=False):
    """Summarize data using the selected operation."""
    try:
        if not group_by_columns:
            st.warning("No grouping columns selected.")
            return pd.DataFrame()

        grouped = df.groupby(group_by_columns)
        results = {}

        for col in selected_columns:
            if selected_operation == "Min":
                results[col] = grouped[col].min()
            elif selected_operation == "Max":
                results[col] = grouped[col].max()
            elif selected_operation == "Sum":
                results[col] = grouped[col].sum()
            elif selected_operation == "Count":
                results[col] = grouped[col].count()
            elif selected_operation == "Average":
                results[col] = grouped[col].mean()
            elif selected_operation == "Median":
                results[col] = grouped[col].median()
            elif selected_operation == "Standard Deviation":
                results[col] = grouped[col].std()

        summary_df = pd.concat(results, axis=1).reset_index()

        if include_all_columns:
            extra_cols = [col for col in df.columns if col not in selected_columns + group_by_columns]
            for col in extra_cols:
                # Instead of inserting column-by-column, collect all columns first
             summary_df = grouped.first().reset_index().copy()
        return summary_df

    except Exception as e:
        st.error(f"Error during summarization: {e}")
        return pd.DataFrame()

# Streamlit UI - Page Title
st.markdown(
    """
    <div style="background-color:#94e399;padding:15px;border-radius:10px;text-align:center;font-size:30px;">
    📑 File Operations Tool
    </div>
    """,
    unsafe_allow_html=True
)

# User chooses an operation
operation = st.radio("Choose an operation:", ["Append Files", "Summarize Data"])

# Global variable to store appended data
if "combined_df" not in st.session_state:
    st.session_state.combined_df = None

# Append Files Section
if operation == "Append Files":
    st.subheader("📁 Append multiple files")
    uploaded_files = st.file_uploader("Upload files (CSV/XLSX/XLS)", type=["csv", "xlsx", "xls"], accept_multiple_files=True)

    selected_sheets = {}
    
    if uploaded_files:
        for file in uploaded_files:
            if file.name.endswith(("xlsx", "xls")):
                sheet_names = read_excel(file)
                if sheet_names and len(sheet_names) > 1:
                    selected_sheets[file.name] = st.selectbox(f"Select a sheet for {file.name}:", options=sheet_names)
                elif sheet_names:
                    selected_sheets[file.name] = sheet_names[0]

    if st.button("Append Files") and uploaded_files:
        st.session_state.combined_df = append_files(uploaded_files, selected_sheets)

        if st.session_state.combined_df is not None:
            st.write("### Preview of Combined Data")
            st.dataframe(preview_dataframe(st.session_state.combined_df))
            
            output_filename = "combined_data.csv"
            output_csv_path = os.path.join(TEMP_DIR, output_filename)
            st.session_state.combined_df.to_csv(output_csv_path, index=False)

            with open(output_csv_path, "rb") as f:
                st.download_button("Download Combined File", data=f, file_name=output_filename, mime="text/csv")

# Summarize Data Section
elif operation == "Summarize Data":
    st.subheader("📊 Summarize Data")

    df = None  # Ensure df is initialized

    col1, col2 = st.columns([1, 2])  # Left: Upload & Config, Right: Data Preview & Summary

    with col1:
        # Checkbox to use combined file
        use_combined = st.checkbox("Use Appended File for Summarization", value=False)

        if use_combined and st.session_state.combined_df is not None:
            df = st.session_state.combined_df
        else:
            file = st.file_uploader("OR Upload a new file (CSV/XLSX/XLS)", type=["csv", "xlsx", "xls"])
            if file:
                if file.name.endswith(".csv"):
                    df = read_csv(file)
                else:
                    sheet_names = read_excel(file)
                    if sheet_names:
                        sheet_name = st.selectbox("Select a sheet:", options=sheet_names)
                        df = load_excel_sheet(file, sheet_name)

    if df is not None:
        with col2:
            st.write("### 📋 Data Preview")
            st.dataframe(preview_dataframe(df))

        with col1:
            numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()
            all_columns = df.columns.tolist()

            group_by_columns = st.multiselect("Select columns to group by:", all_columns)
            selected_columns = st.multiselect("Select numeric columns to summarize:", numeric_columns)
            selected_operation = st.selectbox("Select summarization operation:", ["Min", "Max", "Sum", "Count", "Average", "Median", "Standard Deviation"])
            include_all_columns = st.checkbox("Include All Columns", value=False)

        with col2:
            if st.button("Summarize Data"):
                summary_results = summarize_csv_files(df, selected_operation, selected_columns, group_by_columns, include_all_columns)
                
                st.write("### 📊 Summarized Data")
                st.dataframe(summary_results)

                if not summary_results.empty:
                    csv = summary_results.to_csv(index=False).encode("utf-8")
                    st.download_button("Download Summary", csv, "summary_results.csv", "text/csv")
