import os
import pandas as pd
import streamlit as st
from typing import List, Dict, Optional
 
# Set Streamlit page configuration
st.set_page_config(
    page_title="📑 File Operations Tool",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded"
)
 
# Cache data to improve speed for file operations
@st.cache_data(show_spinner=False)
def read_csv(file_path: str) -> Optional[pd.DataFrame]:
    """Read a CSV file."""
    try:
        return pd.read_csv(file_path, encoding="ISO-8859-1")
    except Exception as e:
        st.error(f"Error reading CSV file '{file_path}': {e}")
        return None
 
@st.cache_data(show_spinner=False)
def read_excel(file_path: str) -> Optional[List[str]]:
    """Read an Excel file and return serializable sheet names."""
    try:
        excel_file = pd.ExcelFile(file_path, engine="openpyxl")
        return excel_file.sheet_names
    except Exception as e:
        st.error(f"Error reading Excel file '{file_path}': {e}")
        return None
 
def load_excel_sheet(file_path: str, sheet_name: str) -> Optional[pd.DataFrame]:
    """Load a specific sheet from an Excel file (not cached due to unserializable object)."""
    try:
        excel_file = pd.ExcelFile(file_path, engine="openpyxl")
        return excel_file.parse(sheet_name)
    except Exception as e:
        st.error(f"Error reading sheet '{sheet_name}': {e}")
        return None
 
@st.cache_data(show_spinner=False)
def validate_columns(dfs: List[pd.DataFrame]) -> bool:
    """Validate if all dataframes have identical columns."""
    if not dfs:
        return False
    columns_list = [set(df.columns) for df in dfs]
    return all(cols == columns_list[0] for cols in columns_list)
 
@st.cache_data(show_spinner=False)
def append_files(file_paths: List[str], selected_sheets: Dict[str, str]) -> Optional[pd.DataFrame]:
    """Append files with column validation."""
    dfs = []
    for file_path in file_paths:
        if file_path.endswith(("xlsx", "xls")):
            sheet_name = selected_sheets.get(os.path.basename(file_path))
            if sheet_name:
                df = load_excel_sheet(file_path, sheet_name)
                if df is not None:
                    dfs.append(df)
        else:
            df = read_csv(file_path)
            if df is not None:
                dfs.append(df)
 
    if not dfs:
        st.error("No valid data frames to combine.")
        return None
 
    if validate_columns(dfs):
        return pd.concat(dfs, axis=0, ignore_index=True)
    else:
        st.error("Column mismatch detected. Ensure all files have the same columns.")
        return None
 
def preview_dataframe(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Preview the first few rows of a dataframe."""
    return df.head(n)
 
def summarize_csv_files(
    df: pd.DataFrame,
    operation: str,
    selected_columns: List[str],
    group_by_columns: List[str],
    include_all_columns: bool
) -> pd.DataFrame:
    """Summarize data based on selected operation and grouping."""
    try:
        operation_map = {
            "Min": "min",
            "Max": "max",
            "Sum": "sum",
            "Count": "count",
            "Mean": "mean",
            "Median": "median",
            "Std": "std"
        }
       
        if include_all_columns:
            # Include non-numeric columns in groupby
            agg_dict = {col: operation_map[operation] for col in selected_columns}
            for col in df.columns:
                if col not in selected_columns and col not in group_by_columns:
                    agg_dict[col] = 'first'
           
            result = df.groupby(group_by_columns, as_index=False).agg(agg_dict)
        else:
            # Only summarize selected numeric columns
            result = df.groupby(group_by_columns, as_index=False)[selected_columns].agg(operation_map[operation])
       
        return result
    except Exception as e:
        st.error(f"Error during summarization: {e}")
        return pd.DataFrame()
 
# Streamlit UI Design
st.markdown("""<style>
    .file-operation-title {
        background-color: #94e399;
        padding: 15px;
        border-radius: 10px;
        font-size: 35px;
        font-weight: bold;
        color: #383232;
        text-align: center;
        margin-bottom: 20px;
    }
    .stRadio > div {
        flex-direction: row;
        gap: 1rem;
    }
</style>""", unsafe_allow_html=True)
 
st.markdown('<div class="file-operation-title">📑 File Operations Tool</div>', unsafe_allow_html=True)
 
# Main Operation Selection
operation = st.radio("Choose an operation:", ["Append Files", "Summarize Data"])
 
# Create temp folder for file operations
temp_folder = "temp_uploaded_files"
os.makedirs(temp_folder, exist_ok=True)
 
# Handling "Append Files" Operation
if operation == "Append Files":
    st.subheader("📁 Append multiple files into a single file")
    uploaded_files = st.file_uploader("Upload files (CSV/XLSX/XLS)", type=["csv", "xlsx", "xls"], accept_multiple_files=True)
    output_filename = st.text_input("Output CSV file name (including .csv extension)", "combined_file.csv")
 
    selected_sheets = {}
 
    if uploaded_files:
        for file in uploaded_files:
            file_path = os.path.join(temp_folder, file.name)
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
 
            # Handle Excel files with multiple sheets
            if file.name.endswith(("xlsx", "xls")):
                sheet_names = read_excel(file_path)
                if sheet_names and len(sheet_names) > 1:
                    sheet_name = st.selectbox(
                        f"Select a sheet for '{file.name}':",
                        options=sheet_names,
                        key=f"{file.name}_sheet_selector"
                    )
                    selected_sheets[file.name] = sheet_name
                    # Preview the selected sheet
                    if sheet_name:
                        sheet_df = load_excel_sheet(file_path, sheet_name)
                        st.write(f"Preview of '{sheet_name}' from '{file.name}':")
                        st.dataframe(preview_dataframe(sheet_df))
                elif sheet_names:
                    selected_sheets[file.name] = sheet_names[0]
                    sheet_df = load_excel_sheet(file_path, sheet_names[0])
                    st.write(f"Preview of '{sheet_names[0]}' from '{file.name}':")
                    st.dataframe(preview_dataframe(sheet_df))
 
        if st.button("Append Files"):
            if output_filename:
                file_paths = [os.path.join(temp_folder, file.name) for file in uploaded_files]
                combined_df = append_files(file_paths, selected_sheets)
 
                if combined_df is not None:
                    st.write("### Preview of Combined Data")
                    st.dataframe(preview_dataframe(combined_df, n=5))
 
                    output_csv_path = os.path.join(temp_folder, output_filename)
                    combined_df.to_csv(output_csv_path, index=False)
 
                    with open(output_csv_path, "rb") as f:
                        st.download_button(
                            label="Download Combined File",
                            data=f,
                            file_name=output_filename,
                            mime="text/csv"
                        )
 
                    use_combined_file = st.radio(
                        "Do you want to use the appended file for summarization?",
                        ["Yes", "No"],
                        key="use_combined_file"
                    )
 
                    if use_combined_file == "Yes":
                        st.session_state["summarize_df"] = combined_df
                        st.success("Appended file is ready for summarization!")
                    else:
                        st.session_state["summarize_df"] = None
                        st.success("You can upload a new file for summarization.")
            else:
                st.error("Please provide an output file name.")
 
# Handling "Summarize Data" Operation
elif operation == "Summarize Data":
    st.subheader("📊 Summarize data")
 
    # Use appended file or upload a new file
    if "summarize_df" in st.session_state and st.session_state["summarize_df"] is not None:
        df = st.session_state["summarize_df"]
        st.write("### Using the appended file for summarization.")
    else:
        file = st.file_uploader("Upload a file (CSV/XLSX/XLS)", type=["csv", "xlsx", "xls"])
        if file:
            temp_path = os.path.join(temp_folder, file.name)
            with open(temp_path, "wb") as f:
                f.write(file.getbuffer())
 
            sheet_name = None
            if file.name.endswith(("xlsx", "xls")):
                sheet_names = read_excel(temp_path)
                if sheet_names and len(sheet_names) > 1:
                    sheet_name = st.selectbox(f"Select a sheet for '{file.name}':", options=sheet_names)
                elif sheet_names:
                    sheet_name = sheet_names[0]
 
            df = load_excel_sheet(temp_path, sheet_name) if sheet_name else read_csv(temp_path)
 
    if df is not None:
        st.write("### Preview of Uploaded Data")
        st.dataframe(preview_dataframe(df))
 
        numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()
        all_columns = df.columns.tolist()
 
        with st.sidebar:
            st.write("### Data Summarization Options")
            group_by_columns = st.multiselect("Select columns to group by:", options=all_columns)
            selected_columns = st.multiselect("Select numeric columns to summarize:", options=numeric_columns)
            summarization_operations = ["Min", "Max", "Sum", "Count", "Mean", "Median", "Std"]
            selected_operation = st.selectbox("Select summarization operation:", summarization_operations)
            include_all_columns = st.checkbox("Include All Columns in Output", value=False)
 
            if st.button("Summarize Data"):
                if selected_columns and group_by_columns:
                    summary_results = summarize_csv_files(
                        df, selected_operation, selected_columns, group_by_columns, include_all_columns
                    )
 
                    if not summary_results.empty:
                        st.write("### Summary Results")
                        st.dataframe(summary_results)
                        csv = summary_results.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "Download Summarized Data",
                            csv,
                            "summary_results.csv",
                            "text/csv"
                        )
                else:
                    st.warning("Please select at least one numeric column to summarize and one column to group by.")