# pages/Geospatial Mapping.py
import streamlit as st
import pandas as pd
import io
from github import Github
import plotly.express as px
import pgeocode

# --- CONFIG ---
GITHUB_TOKEN = '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'
REPO_NAME = 'CooperRuff/RAMStreamlit'
FILE_PATH = 'Combined_RAM_Services_with_zip.csv'

st.title("📍 RAM Clinic Pins by ZIP Code and Year")

try:
    # --- Connect to GitHub and load CSV ---
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    contents = repo.get_contents(FILE_PATH)
    
    # Load only the needed columns to avoid duplicate column name issues
    df_all = pd.read_csv(io.StringIO(contents.decoded_content.decode()), dtype=str)
    needed_cols = ["zip code", "Clinic", "Year"]
    df = df_all[needed_cols].copy()

    # --- Clean and prep ---
    df = df.dropna(subset=["zip code", "Clinic", "Year"])
    df["zip code"] = df["zip code"].astype(str).str.zfill(5)
    df["Clinic"] = df["Clinic"].str.strip()
    df["Year"] = df["Year"].astype(str).str.strip()
    df = df[~df["Year"].str.contains("RAMPatientQuestions", case=False, na=False)]


    # --- Filter by year ---
    years = sorted(df["Year"].unique())
    selected_years = st.multiselect("Select Year(s)", years, default=years)
    df = df[df["Year"].isin(selected_years)]

    # --- Geocode ZIPs ---
    st.info("📍 Geocoding ZIP codes...")
    nomi = pgeocode.Nominatim("us")
    df["latitude"] = df["zip code"].apply(lambda z: nomi.query_postal_code(z).latitude)
    df["longitude"] = df["zip code"].apply(lambda z: nomi.query_postal_code(z).longitude)
    df = df.dropna(subset=["latitude", "longitude"])

    # --- Drop duplicates (one point per Clinic per Year per ZIP) ---
    df = df.drop_duplicates(subset=["zip code", "Clinic", "Year"])

    # --- Plot pin map ---
    st.subheader("🧭 RAM Clinics on the Map")

    fig = px.scatter_mapbox(
        df,
        lat="latitude",
        lon="longitude",
        color="Year",
        hover_name="Clinic",
        zoom=3.5,
        center=dict(lat=37.8, lon=-96),
        mapbox_style="open-street-map",
        height=700
    )

    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"❌ Error generating map: {e}")
