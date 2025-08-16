# pages/Graphs.py
import streamlit as st
import pandas as pd
import io
from github import Github
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from io import BytesIO

# --- CONFIGURATION ---
GITHUB_TOKEN = st.secrets["password"]
REPO_NAME = 'CooperRuff/RAMStreamlit'
FILE_PATH = 'Combined_RAM_Services_with_zip.csv'

# --- QUESTION PREFIXES ---
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

# --- HELPER: Chart Downloader ---
def render_plotly_chart(fig, filename_hint):
    st.plotly_chart(fig)
    buf = BytesIO()
    fig.write_image(buf, format="png")
    buf.seek(0)
    st.download_button(
        label="📥 Download Chart as PNG",
        data=buf,
        file_name=f"{filename_hint}.png",
        mime="image/png"
    )

# --- MAIN APP ---
st.title("📈 RAM Data Graphs")

try:
    # --- Load from GitHub ---
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    contents = repo.get_contents(FILE_PATH)
    df = pd.read_csv(io.StringIO(contents.decoded_content.decode()))
    df.columns = df.columns.str.strip()

    # --- Clean Year ---
    df = df[df["Year"].notna()]
    df["Year"] = df["Year"].astype(str).str.strip()
    df = df[~df["Year"].str.contains("RAMPatientQuestions", case=False, na=False)]

    # --- Year Filter ---
    selected_years = st.multiselect(
        "Select Year(s)", options=sorted(df["Year"].unique()), default=sorted(df["Year"].unique())
    )
    filtered_df = df[df["Year"].isin(selected_years)] if selected_years else df

    # --- Chart Type ---
    st.subheader("📊 Custom Graph")
    all_columns = df.columns.tolist()
    chart_type = st.selectbox(
        "Chart Type", ["Bar", "Line", "Area", "Scatterplot", "Univariate", "Question Charts"], index=0
    )

    # ---------------------------
    # UNIVARIATE CHART TYPE
    # ---------------------------
    if chart_type == "Univariate":
        single_axis = st.selectbox("Select Variable", all_columns)
        uni_chart_type = st.selectbox("Chart Style", ["Pie", "Bar (Total)", "Line (Yearly)"])

        if single_axis in filtered_df.columns:
            filtered_df[single_axis] = pd.to_numeric(filtered_df[single_axis], errors="coerce")
            year_summary = filtered_df.groupby("Year")[single_axis].sum().reset_index()

            if uni_chart_type == "Pie":
                fig = px.pie(year_summary, names="Year", values=single_axis,
                             title=f"{single_axis} Totals by Year")
            elif uni_chart_type == "Bar (Total)":
                total = filtered_df[single_axis].sum()
                fig = px.bar(x=[single_axis], y=[total],
                             labels={"x": "Variable", "y": "Total"},
                             title=f"Total {single_axis} Across All Years")
            elif uni_chart_type == "Line (Yearly)":
                fig = px.line(year_summary, x="Year", y=single_axis,
                              title=f"{single_axis} Over Time")

            render_plotly_chart(fig, filename_hint=f"{single_axis}_{uni_chart_type.replace(' ', '_')}")

    # ---------------------------
    # QUESTION CHART TYPE
    # ---------------------------
    elif chart_type == "Question Charts":
        question_map = {}
        for prefix in QUESTION_PREFIXES:
            matches = [col for col in all_columns if col.startswith(prefix + " - ")]
            if matches:
                question_map[prefix] = matches

        selected_question = st.selectbox("Select Question", list(question_map.keys()))
        question_chart_type = st.selectbox("Chart Style", ["Pie", "Bar (Grouped by Year)", "Bar (Stacked)"])

        if selected_question in question_map:
            question_cols = question_map[selected_question]
            pie_data = filtered_df[["Year"] + question_cols].copy()
            pie_data[question_cols] = pie_data[question_cols].apply(pd.to_numeric, errors="coerce")

            if question_chart_type == "Pie":
                totals = pie_data[question_cols].sum().reset_index()
                totals.columns = ["Answer", "Count"]
                totals["Answer"] = totals["Answer"].str.replace(f"{selected_question} - ", "")
                fig = px.pie(totals, names="Answer", values="Count",
                             title=f"{selected_question} Responses")
                render_plotly_chart(fig, filename_hint=f"{selected_question}_pie")
            elif question_chart_type == "Bar (Grouped by Year)":
                grouped = pie_data.groupby("Year")[question_cols].sum().reset_index()
                melted = grouped.melt(id_vars="Year", var_name="Answer", value_name="Count")
                melted["Answer"] = melted["Answer"].str.replace(f"{selected_question} - ", "")
                fig = px.bar(melted, x="Answer", y="Count", color="Year", barmode="group",
                             title=f"{selected_question} Responses by Year")
                render_plotly_chart(fig, filename_hint=f"{selected_question}_bar_grouped")
            elif question_chart_type == "Bar (Stacked)":
                grouped = pie_data.groupby("Year")[question_cols].sum().reset_index()
                melted = grouped.melt(id_vars="Year", var_name="Answer", value_name="Count")
                melted["Answer"] = melted["Answer"].str.replace(f"{selected_question} - ", "")
                fig = px.bar(
                    melted,
                    x="Year",
                    y="Count",
                    color="Answer",
                    barmode="stack",
                    title=f"{selected_question} Responses by Year (Stacked)"
                )
                render_plotly_chart(fig, filename_hint=f"{selected_question}_bar_stacked")


    # ---------------------------
    # MULTIVARIATE CHART TYPES
    # ---------------------------
    else:
        x_axis = st.selectbox("Select X-axis", all_columns, index=0)
        y_axes = st.multiselect("Select Y-axis Variable(s)", all_columns, default=[all_columns[1]])
        valid_y_axes = [col for col in y_axes if col in filtered_df.columns]

        if x_axis in filtered_df.columns and valid_y_axes:
            plot_df = filtered_df[[x_axis] + valid_y_axes].copy()
            for col in valid_y_axes:
                plot_df[col] = pd.to_numeric(plot_df[col], errors="coerce")
            plot_df = plot_df.dropna(subset=valid_y_axes)

            if chart_type == "Scatterplot":
                if len(valid_y_axes) != 1:
                    st.warning("⚠️ Select exactly one Y-axis for scatterplot.")
                else:
                    y_col = valid_y_axes[0]
                    x_vals = pd.to_numeric(plot_df[x_axis], errors='coerce')
                    y_vals = pd.to_numeric(plot_df[y_col], errors='coerce')
                    scatter_df = pd.DataFrame({x_axis: x_vals, y_col: y_vals}).dropna()

                    if scatter_df.empty:
                        st.warning("⚠️ No numeric data to plot.")
                    else:
                        # Linear regression
                        x_np = scatter_df[x_axis].values
                        y_np = scatter_df[y_col].values
                        m, b = np.polyfit(x_np, y_np, 1)
                        y_pred = m * x_np + b
                        r_squared = 1 - np.sum((y_np - y_pred) ** 2) / np.sum((y_np - np.mean(y_np)) ** 2)

                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=x_np, y=y_np, mode='markers', name='Data'))
                        fig.add_trace(go.Scatter(x=[0, max(x_np)], y=[m*0+b, m*max(x_np)+b],
                                                 mode='lines', name='Best Fit Line'))

                        fig.update_layout(
                            title=f"{y_col} vs {x_axis} with Best Fit Line",
                            xaxis_title=x_axis,
                            yaxis_title=y_col,
                            xaxis=dict(range=[0, max(x_np)*1.05]),
                            yaxis=dict(range=[0, max(y_np)*1.05])
                        )

                        render_plotly_chart(fig, filename_hint=f"{y_col}_vs_{x_axis}_scatter")

                        st.markdown(f"**Linear Regression Equation:**  \n`y = {m:.3f}x + {b:.3f}`")
                        st.markdown(f"**R² = {r_squared:.4f}**")

            else:
                grouped = plot_df.groupby(x_axis).sum(numeric_only=True).reset_index()
                chart_title = f"{chart_type} Chart: {', '.join(valid_y_axes)} by {x_axis}"

                if chart_type == "Bar":
                    fig = px.bar(grouped, x=x_axis, y=valid_y_axes, barmode="group", title=chart_title)
                elif chart_type == "Line":
                    fig = px.line(grouped, x=x_axis, y=valid_y_axes, title=chart_title)
                elif chart_type == "Area":
                    fig = px.area(grouped, x=x_axis, y=valid_y_axes, title=chart_title)

                render_plotly_chart(fig, filename_hint=f"{chart_type}_{'_'.join(valid_y_axes)}_by_{x_axis}")

except Exception as e:
    st.error(f"❌ Error loading data: {e}")
