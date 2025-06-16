# resource_planner.py
import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Resource Planner", layout="centered")

st.title("🗓️ Resource Planner")

if "data" not in st.session_state:
    st.session_state.data = []

st.subheader("Enter Estimated Hours")
with st.form("entry_form"):
    name = st.text_input("Your Name")
    week = st.date_input("Week Starting", value=date.today())
    project = st.text_input("Project Name")
    status = st.selectbox("Status", ["Confirmed", "Tentative"])
    hours = st.number_input("Estimated Hours", min_value=0.0, step=0.5)
    submitted = st.form_submit_button("Submit")

if submitted:
    st.session_state.data.append(
        {
            "Name": name,
            "Week": week,
            "Project": project,
            "Status": status,
            "Estimated Hours": hours,
        }
    )
    st.success("Entry submitted!")

st.subheader("Manager View")
df = pd.DataFrame(st.session_state.data)
if not df.empty:
    st.dataframe(df)
else:
    st.write("No data submitted yet.")
