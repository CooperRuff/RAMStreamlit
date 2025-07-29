# pages/Graphs.py
import streamlit as st
import pandas as pd
import io
from github import Github

# CONFIGURATION
GITHUB_TOKEN = 'your_token_here'
REPO_NAME = 'CooperRuff/RAMStreamlit'
FILE_PATH = 'Combined_RAM_Services.csv'
KEYWORDS = ["Glasses", "Extractions", "Fillings", "Cleanings", "Medical Exams"]

st.title("📈 RAM Data Graphs")

try:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    contents = repo.get_contents(FILE_PATH)

    df = pd.read_csv(io.StringIO(contents.decoded_content.decode()))
    df = df[df["Year"].notna()]
    df["Year"] = df["Year"].astype(str)

    selected_year = st.selectbox("Select Year", sorted(df["Year"].unique()), key="graph_year")

    st.subheader(f"Total Services by Clinic – {selected_year}")
    for kw in KEYWORDS:
        if kw in df.columns:
            st.markdown(f"**{kw}**")
            chart_df = df[df["Year"] == selected_year][["Clinic", kw]]
            chart_df = chart_df.groupby("Clinic").sum().sort_values(kw, ascending=False)
            st.bar_chart(chart_df)

except Exception as e:
    st.error(f"Error loading data for graphs: {e}")
