import streamlit as st
import pandas as pd
import os
import subprocess

# Title
st.title("RAM Analytics")

# Load existing CSV from GitHub
@st.cache_data
def load_combined_data():
    url = "https://raw.githubusercontent.com/CooperRuff/RAMStreamlit/main/Combined_RAM_Services.csv"
    return pd.read_csv(url)

combined_df = load_combined_data()

# Load ZIP reference files
ref_df = pd.read_csv("https://raw.githubusercontent.com/CooperRuff/RAMStreamlit/main/uscities.csv")
ref_df["city_lower"] = ref_df["city"].str.lower()
zip_pop_df = pd.read_csv("https://raw.githubusercontent.com/CooperRuff/RAMStreamlit/main/population_by_zip_2010.csv.gz", compression='gzip')
zip_pop_df["zipcode"] = zip_pop_df["zipcode"].astype(str)

# ZIP functions
def get_zipcode(city_state):
    try:
        city, state = map(str.strip, city_state.split(','))
        matches = ref_df[(ref_df["city_lower"] == city.lower()) & (ref_df["state_id"] == state.upper())]
        if matches.empty:
            return "0"
        zip_string = str(matches.sort_values("population", ascending=False).iloc[0]["zips"])
        return zip_string.strip()
    except Exception as e:
        print(f"Error for {city_state}: {e}")
        return "0"

def get_largest_zip(zip_string):
    try:
        zip_list = str(zip_string).split()
        matches = zip_pop_df[zip_pop_df["zipcode"].isin(zip_list)]
        if matches.empty:
            return "0"
        return matches.sort_values("population", ascending=False).iloc[0]["zipcode"]
    except Exception as e:
        print(f"Error processing ZIPs: {zip_string}, {e}")
        return "0"

# Extract data from Excel
def extract_from_excel(file, year, location):
    xl = pd.ExcelFile(file)
    row = {col: 0 for col in combined_df.columns if col not in ["File", "Year", "Location", "Zips", "zip code"]}
    row.update({
        "File": os.path.basename(file.name),
        "Year": year,
        "Location": location,
    })

    acceptable_service_sheets = ['Service Numbers', 'Service Number', 'Service Number ', 'Service Number Summary']
    for sheet in xl.sheet_names:
        if sheet.strip() in acceptable_service_sheets:
            df = xl.parse(sheet)
            if df.shape[1] >= 3:
                df.columns = [str(c).strip() for c in df.columns]
                for i in range(len(df)):
                    service_name = str(df.iloc[i, 1]).strip()
                    try:
                        value = float(df.iloc[i, 2])
                    except:
                        continue
                    if service_name in combined_df.columns:
                        row[service_name] += value

    if 'Answer Counts (DNP)' in xl.sheet_names:
        try:
            df = xl.parse('Answer Counts (DNP)', keep_default_na=False, na_values=[])
        except Exception as e:
            print(f"Error reading 'Answer Counts (DNP)' sheet: {e}")
            df = pd.DataFrame()

        if not df.empty and df.shape[1] >= 3:
            main = pd.DataFrame(columns=['Cell1', 'Cell2', 'Sum'])
            file_id = os.path.basename(file.name)

            for _, trial_row in df.iterrows():
                if len(trial_row) < 3:
                    continue
                cell1, cell2, cell3 = trial_row.iloc[0], trial_row.iloc[1], trial_row.iloc[2]

                match = main[(main['Cell1'] == cell1) & (main['Cell2'] == cell2)]
                if not match.empty:
                    main_index = match.index[0]
                    main.at[main_index, file_id] = cell3
                else:
                    new_row = pd.DataFrame({'Cell1': [cell1], 'Cell2': [cell2], 'Sum': [0], file_id: [cell3]})
                    main = pd.concat([main, new_row], ignore_index=True)

            for i in range(len(main)):
                if main.shape[1] > 3:
                    sum_value = main.iloc[i, 3:].apply(pd.to_numeric, errors='coerce').sum()
                    main.at[i, 'Sum'] = sum_value

            for _, row_entry in main.iterrows():
                service_name = str(row_entry['Cell2']).strip()
                value = pd.to_numeric(row_entry['Sum'], errors='coerce') or 0
                if service_name in combined_df.columns:
                    row[service_name] += value

    for sheet in ['One Pager', 'One Pager Summary']:
        if sheet in xl.sheet_names:
            df = xl.parse(sheet)
            for col in df.columns:
                name = str(col).strip().lower()
                if "glass" in name:
                    row["Glasses"] += pd.to_numeric(df[col], errors='coerce').sum(min_count=1) or 0
                elif "extract" in name:
                    row["Extractions"] += pd.to_numeric(df[col], errors='coerce').sum(min_count=1) or 0
                elif "fill" in name:
                    row["Fillings"] += pd.to_numeric(df[col], errors='coerce').sum(min_count=1) or 0
                elif "clean" in name:
                    row["Cleanings"] += pd.to_numeric(df[col], errors='coerce').sum(min_count=1) or 0
                elif "medical" in name:
                    row["Medical Exams"] += pd.to_numeric(df[col], errors='coerce').sum(min_count=1) or 0

    zip_string = get_zipcode(location)
    row["Zips"] = zip_string
    row["zip code"] = get_largest_zip(zip_string)
    return pd.DataFrame([row])

# Section: Aggregate Summary Table
st.subheader("Summary of Services Provided")

service_cols = ["Glasses", "Extractions", "Fillings", "Cleanings", "Medical Exams"]
combined_df["Year"] = combined_df["Year"].astype(str)
total_sum = combined_df[service_cols].sum()
year_input_temp = st.text_input("Enter Year (for summary above)")

if year_input_temp.strip():
    year_filtered = combined_df[combined_df["Year"] == year_input_temp.strip()]
    year_sum = year_filtered[service_cols].sum()
else:
    year_sum = pd.Series([0]*len(service_cols), index=service_cols)

summary_df = pd.DataFrame({
    "All Years": total_sum,
    f"Year: {year_input_temp.strip() or 'N/A'}": year_sum
})

st.dataframe(summary_df)

# Upload section
st.subheader("Upload New Clinic Data")

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx", "xls"])
year_input = st.text_input("Enter Year")
location_input = st.text_input("Enter Location")

if uploaded_file and year_input.strip() and location_input.strip():
    if st.button("Submit"):
        try:
            new_row = extract_from_excel(uploaded_file, year_input.strip(), location_input.strip())
            updated_df = pd.concat([combined_df, new_row], ignore_index=True)
            updated_df.to_csv("Combined_RAM_Services.csv", index=False)

            subprocess.run(["git", "config", "--global", "user.name", "streamlit-bot"])
            subprocess.run(["git", "config", "--global", "user.email", "streamlit@bot.com"])
            subprocess.run(["git", "add", "Combined_RAM_Services.csv"])
            subprocess.run(["git", "commit", "-m", "Update Combined_RAM_Services with new submission"])
            subprocess.run(["git", "push"])

            st.success("Data extracted, saved, and pushed to GitHub!")
            st.dataframe(new_row)
        except Exception as e:
            st.error(f"Error processing submission: {e}")
else:
    st.info("Please upload a file, enter a year, and provide a location before submitting.")
