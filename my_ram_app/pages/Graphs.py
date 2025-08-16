import streamlit as st
import pandas as pd
import io
from github import Github
import pydeck as pdk

# CONFIGURATION
GITHUB_TOKEN = 'your_token_here'
REPO_NAME = 'CooperRuff/RAMStreamlit'
FILE_PATH = 'Combined_RAM_Services.csv'
KEYWORDS = ["Glasses", "Extractions", "Fillings", "Cleanings", "Medical Exams"]

st.title("🗺️ RAM Clinic Map & Totals")

try:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    contents = repo.get_contents(FILE_PATH)

    df = pd.read_csv(io.StringIO(contents.decoded_content.decode()))
    df = df[df["Year"].notna()]
    df["Year"] = df["Year"].astype(str)

    selected_year = st.selectbox("Select Year", sorted(df["Year"].unique()))

    df = df[df["Year"] == selected_year].copy()
    df["Total Services"] = df[KEYWORDS].sum(axis=1)

    if "Latitude" not in df.columns or "Longitude" not in df.columns:
        st.warning("⚠️ Latitude and Longitude columns are required for mapping.")
    else:
        st.subheader("🧭 Clinic Map")
        map_df = df[["Clinic", "Latitude", "Longitude", "Total Services"]].dropna()

        st.pydeck_chart(pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v9",
            initial_view_state=pdk.ViewState(
                latitude=map_df["Latitude"].mean(),
                longitude=map_df["Longitude"].mean(),
                zoom=5,
                pitch=50,
            ),
            layers=[
                pdk.Layer(
                    'ScatterplotLayer',
                    data=map_df,
                    get_position='[Longitude, Latitude]',
                    get_radius='Total Services',
                    get_fill_color='[200, 30, 0, 160]',
                    pickable=True,
                    radius_scale=10,
                ),
            ],
            tooltip={"text": "{Clinic}\nServices: {Total Services}"}
        ))

        st.subheader("🏥 Top Clinics by Total Services")
        top_df = map_df.sort_values("Total Services", ascending=False)[["Clinic", "Total Services"]]
        st.bar_chart(top_df.set_index("Clinic"))

except Exception as e:
    st.error(f"Error loading data for graphs: {e}")
