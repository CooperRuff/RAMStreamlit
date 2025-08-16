# pages/Geospatial Mapping.py
import streamlit as st
import pandas as pd
import io
from github import Github
import plotly.express as px
import pgeocode

# --- CONFIG ---
GITHUB_TOKEN = st.secrets["password"]
REPO_NAME = 'CooperRuff/RAMStreamlit'
FILE_PATH = 'Combined_RAM_Services_with_zip.csv'

st.title("📍 RAM Clinic Pins by ZIP Code and Year")

# ---------------------- HELPER FUNCTION TO LOAD DATA ----------------------
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_github_data():
    """Load data from GitHub with error handling"""
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        
        # Load only the needed columns to avoid duplicate column name issues
        df_all = pd.read_csv(io.StringIO(contents.decoded_content.decode()), dtype=str)
        needed_cols = ["zip code", "Clinic", "Year"]
        
        # Check if all needed columns exist
        missing_cols = [col for col in needed_cols if col not in df_all.columns]
        if missing_cols:
            return None, f"Missing required columns: {missing_cols}"
        
        df = df_all[needed_cols].copy()
        return df, None
    except Exception as e:
        return None, str(e)

try:
    # --- Load data using helper function ---
    df, error = load_github_data()
    
    if error:
        st.error(f"❌ Unable to load data from GitHub: {error}")
        st.info("💡 Please check your GitHub token and ensure it has the necessary permissions.")
    else:
        # --- Clean and prep ---
        df = df.dropna(subset=["zip code", "Clinic", "Year"])
        df["zip code"] = df["zip code"].astype(str).str.zfill(5)
        df["Clinic"] = df["Clinic"].str.strip()
        df["Year"] = df["Year"].astype(str).str.strip()
        df = df[~df["Year"].str.contains("RAMPatientQuestions", case=False, na=False)]

        # --- Filter by year ---
        years = sorted(df["Year"].unique())
        if not years:
            st.warning("⚠️ No valid years found in the data.")
        else:
            selected_years = st.multiselect("Select Year(s)", years, default=years)
            df = df[df["Year"].isin(selected_years)]

            if df.empty:
                st.warning("⚠️ No data available for selected years.")
            else:
                # --- Geocode ZIPs ---
                st.info("📍 Geocoding ZIP codes...")
                
                # Initialize geocoder
                nomi = pgeocode.Nominatim("us")
                
                # Add progress bar for geocoding
                progress_bar = st.progress(0)
                unique_zips = df["zip code"].unique()
                zip_coords = {}
                
                for i, zip_code in enumerate(unique_zips):
                    try:
                        result = nomi.query_postal_code(zip_code)
                        if not pd.isna(result.latitude) and not pd.isna(result.longitude):
                            zip_coords[zip_code] = {
                                'latitude': result.latitude,
                                'longitude': result.longitude
                            }
                    except Exception as e:
                        st.warning(f"⚠️ Could not geocode ZIP {zip_code}: {e}")
                    
                    progress_bar.progress((i + 1) / len(unique_zips))
                
                # Map coordinates back to dataframe
                df["latitude"] = df["zip code"].map(lambda z: zip_coords.get(z, {}).get('latitude'))
                df["longitude"] = df["zip code"].map(lambda z: zip_coords.get(z, {}).get('longitude'))
                df = df.dropna(subset=["latitude", "longitude"])

                if df.empty:
                    st.error("❌ No valid coordinates found for the provided ZIP codes.")
                else:
                    # --- Drop duplicates (one point per Clinic per Year per ZIP) ---
                    df = df.drop_duplicates(subset=["zip code", "Clinic", "Year"])

                    # --- Plot pin map ---
                    st.subheader("🧭 RAM Clinics on the Map")
                    st.info(f"📊 Showing {len(df)} clinic locations")

                    fig = px.scatter_mapbox(
                        df,
                        lat="latitude",
                        lon="longitude",
                        color="Year",
                        hover_name="Clinic",
                        hover_data={"zip code": True, "latitude": False, "longitude": False},
                        zoom=3.5,
                        center=dict(lat=37.8, lon=-96),
                        mapbox_style="open-street-map",
                        height=700,
                        title="RAM Clinic Locations by Year"
                    )

                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Display summary statistics
                    st.subheader("📈 Summary Statistics")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Total Locations", len(df))
                    with col2:
                        st.metric("Unique Clinics", df["Clinic"].nunique())
                    with col3:
                        st.metric("Years Covered", df["Year"].nunique())

except Exception as e:
    st.error(f"❌ Error generating map: {e}")
    st.info("💡 Please check your data source and try again.")