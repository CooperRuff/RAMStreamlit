# Numbers.py
import numpy as np
import streamlit as st
import pandas as pd
import io
from github import Github

# CONFIGURATION
GITHUB_TOKEN = st.secrets["password"]
REPO_NAME = 'CooperRuff/RAMStreamlit'
FILE_PATH = 'Combined_RAM_Services_with_zip.csv'

KEYWORDS = ["Glasses", "Extractions", "Fillings", "Cleanings", "Medical Exams"]
SERVICE_SHEETS = ['Service Numbers', 'Service Number', 'Service Number ', 'Service Number Summary']
SPECIAL_WORDS = [
    "Composite", "Extraction", "Debridement", "X-Ray", "Cataracts",
    "Diabetes", "Vaccine", "Vaccination", "Readers",
    "Single Vision Glasses", "Mail", "Mailing", "Bifocal"
]
QUESTION_PREFIXES = [
    "Ability", "AlternateEmerRoom", "ChiefComplaint", "Computer", "DentalInsurance",
    "ERVisits", "EmerRoom", "Employment", "EmploymentStatus", "Ethnicity", "GenHealth",
    "GradeLevel", "Health", "HealthChange", "HealthInsurance", "Height", "HomeSize",
    "HouseSize", "HouseholdSize", "How did you hear about this clinic?", "HowHear",
    "Lang", "MaritalStatus", "Military", "Preferred Language", "Ramclinics", "ReasonforRAM",
    "SurveyType", "TranspType", "TravelDistance", "VisionInsurance", "WaitTime", "Weight",
    "What is the patient here for?", "What is your employment status?",
    "When was the last time you saw a dentist?",
    "When was the last time you saw a medical doctor?",
    "When was the last time you saw a vision doctor?", "WhoTold",
    "YearsDental", "YearsMedical", "YearsVision"
]

st.title("📊 RAM Data Uploader")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
year = st.text_input("Enter Year")
location = st.text_input("Enter City/Location")

# ---------------------- PARSING HELPERS ----------------------

def assign_from_sheet(file, sheet_name, fallback_sheet, keywords, col_list):
    try:
        df = pd.read_excel(file, sheet_name=sheet_name, header=None)
    except:
        try:
            df = pd.read_excel(file, sheet_name=fallback_sheet, header=None)
        except:
            return {}

    result = {}
    for keyword in keywords:
        cell = df[df.apply(lambda row: row.astype(str).str.contains(keyword, case=False).any(), axis=1)]
        if not cell.empty:
            idx = cell.index[0]
            col_idx = df.columns[df.iloc[idx].astype(str).str.contains(keyword, case=False)][0]
            value = df.iloc[idx, col_idx + 1]
            result[keyword] = int(value) if pd.notna(value) else 0
    return result

def extract_service_numbers(file, col_list):
    for sheet in SERVICE_SHEETS:
        try:
            df = pd.read_excel(file, sheet_name=sheet, keep_default_na=False)
            break
        except:
            continue
    else:
        return {}

    data = {}
    for _, row in df.iterrows():
        if len(row) < 3:
            continue
        key = f"{row[0]} - {row[1]}"
        value = row[2]
        data[key] = value if pd.notna(value) else 0
    return data

def extract_answer_counts(file, col_list):
    try:
        df = pd.read_excel(file, sheet_name="Answer Counts (DNP)", keep_default_na=False)
    except:
        return {}

    data = {}
    for _, row in df.iterrows():
        if len(row) < 3:
            continue
        key = f"{row[0]} - {row[1]}"
        value = row[2]
        data[key] = value if pd.notna(value) else 0
    return data

def update_total_columns(row_data, all_columns):
    for word in SPECIAL_WORDS:
        matching_cols = [
            col for col in all_columns
            if word.lower() in col.lower() and not col.lower().endswith("_total")
        ]
        total_col = next(
            (col for col in all_columns if col.lower() == f"{word.lower()}_total"),
            None
        )
        if total_col:
            total_sum = 0
            for col in matching_cols:
                val = row_data.get(col, 0)
                try:
                    total_sum += float(val)
                except (ValueError, TypeError):
                    continue
            row_data[total_col] = total_sum

def build_aligned_row(file, location, year, uploaded_filename, existing_columns):
    row_data = {col: 0 for col in existing_columns}
    new_columns = {}

    row_data["Clinic"] = location
    row_data["Year"] = year
    row_data["Expedition Folder"] = location
    row_data["File Name"] = uploaded_filename

    keyword_values = assign_from_sheet(file, "One Pager", "One Pager Summary", KEYWORDS, existing_columns)
    for key, val in keyword_values.items():
        if key in row_data:
            row_data[key] = val
        else:
            new_columns[key] = val

    file.seek(0)
    service_values = extract_service_numbers(file, existing_columns + list(new_columns.keys()))
    for key, val in service_values.items():
        if key in row_data:
            row_data[key] = val
        else:
            new_columns[key] = val

    file.seek(0)
    answer_values = extract_answer_counts(file, existing_columns + list(new_columns.keys()))
    for key, val in answer_values.items():
        if key in row_data:
            row_data[key] = val
        else:
            new_columns[key] = val

    row_data.update(new_columns)
    return row_data, list(new_columns.keys())

# ---------------------- HELPER FUNCTION TO LOAD DATA ----------------------
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_github_data():
    """Load data from GitHub with error handling"""
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        df = pd.read_csv(io.StringIO(contents.decoded_content.decode()))
        return df, None
    except Exception as e:
        return None, str(e)

# ---------------------- MAIN WORKFLOW ----------------------

if uploaded_file and year and location:
    if st.button("Submit and Upload"):
        try:
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            contents = repo.get_contents(FILE_PATH)
            existing_df = pd.read_csv(io.StringIO(contents.decoded_content.decode()))
            existing_columns = existing_df.columns.tolist()

            st.info("⏳ Processing your Excel file...")
            uploaded_file.seek(0)
            new_row_dict, new_keys = build_aligned_row(
                uploaded_file, location, year, uploaded_file.name, existing_columns
            )

            for key in new_keys:
                if key not in existing_df.columns:
                    existing_df[key] = 0

            update_total_columns(new_row_dict, existing_df.columns.tolist())
            new_row = pd.DataFrame([new_row_dict])
            new_row = new_row.reindex(columns=existing_df.columns, fill_value=0)

            updated_df = pd.concat([existing_df, new_row], ignore_index=True)
            csv_buffer = io.StringIO()
            updated_df.to_csv(csv_buffer, index=False)

            repo.update_file(
                path=FILE_PATH,
                message=f"Add data from {uploaded_file.name}",
                content=csv_buffer.getvalue(),
                sha=contents.sha
            )

            st.success("✅ Data added and pushed to GitHub!")
            # Clear cache after successful upload
            st.cache_data.clear()
        except Exception as e:
            st.error(f"🚨 Error: {e}")

# ---------------------- KEYWORD SUMMARY ----------------------

st.subheader("📊 Year-over-Year Keyword Comparison")

try:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    contents = repo.get_contents(FILE_PATH)

    df = pd.read_csv(io.StringIO(contents.decoded_content.decode()))
    df = df[df["Year"].notna()]
    df["Year"] = df["Year"].astype(str)

    available_years = sorted(df["Year"].unique())
    col1, col2 = st.columns(2)
    with col1:
        year_current = st.selectbox("Current Year", options=available_years, index=len(available_years) - 1)
    with col2:
        year_prior = st.selectbox("Prior Year", options=available_years, index=len(available_years) - 2 if len(available_years) > 1 else 0)

    comparison = []
    for kw in KEYWORDS:
        if kw in df.columns:
            current_total = df[df["Year"] == year_current][kw].sum()
            prior_total = df[df["Year"] == year_prior][kw].sum()
            variance = current_total - prior_total
            pct_change = (variance / prior_total * 100) if prior_total != 0 else np.nan
            comparison.append({
                "Keyword": kw,
                f"{year_prior}": int(prior_total),
                f"{year_current}": int(current_total),
                "Variance": int(variance),
                "% Change": f"{pct_change:.1f}%" if not np.isnan(pct_change) else "N/A"
            })

    comp_df = pd.DataFrame(comparison)

    def highlight_large(val):
        try:
            val_float = float(val.strip('%'))
            if abs(val_float) > 25:
                return "color: red; font-weight: bold"
        except:
            return ""
        return ""

    st.dataframe(comp_df.style.applymap(highlight_large, subset=["Variance", "% Change"]).set_properties(**{
        'font-weight': 'bold'
    }, subset=[f"{year_prior}", f"{year_current}"]))
except Exception as e:
    st.warning(f"⚠️ Unable to build year-over-year summary: {e}")
# ---------------------- QUESTION SUMMARY ----------------------

st.subheader("📋 Question Summary Table")

# Use the same loaded data
if df is not None:
    try:
        # Find all question-like columns
        question_map = {}
        all_columns = df.columns.tolist()

        for prefix in QUESTION_PREFIXES:
            matches = [col for col in all_columns if col.startswith(prefix + " - ")]
            if matches:
                question_map[prefix] = matches

        if not question_map:
            st.info("No question-format columns found.")
        else:
            selected_question = st.selectbox("Select a Question", list(question_map.keys()))
            if selected_question in question_map:
                question_cols = question_map[selected_question]
                df_question = df[["Year"] + question_cols].copy()
                df_question[question_cols] = df_question[question_cols].apply(pd.to_numeric, errors="coerce")

                # Group by year and sum
                grouped = df_question.groupby("Year")[question_cols].sum().T
                grouped.index = grouped.index.str.replace(f"{selected_question} - ", "")

                # Add totals row
                grouped["Total"] = grouped.sum(axis=1)

                st.dataframe(grouped)

    except Exception as e:
        st.warning(f"⚠️ Unable to build question summary table: {e}")
else:
    st.warning("⚠️ Unable to load data for question summary table.")