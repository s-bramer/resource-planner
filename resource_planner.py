# main.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
from utils import load_csv, save_csv, pivot_entries, sum_hours
from models import Employee
import numpy as np

# ---- Initialize App ----
st.set_page_config(page_title="Resource Planner", layout="wide")
st.title("🗓️ Resource Planner")

# ---- File Paths ----
ENTRIES_FILE = "data/entries.csv"
SKILLS_FILE = "data/skills.csv"
EMPLOYEES_FILE = "data/employees.csv"

# ---- Precompute Weeks ----
start_date = date.today()
week_dates = [start_date + timedelta(weeks=i) for i in range(12)]
week_strs = [w.strftime("%d %b") for w in week_dates]


# ---- Cached Data Load ----
@st.cache_data
def load_all_data():
    return (
        load_csv(ENTRIES_FILE, ["Employee", "Week", "Project", "Hours", "Status"]),
        load_csv(SKILLS_FILE, ["Employee", "Skill", "Level"]),
        load_csv(EMPLOYEES_FILE, ["Employee"]),
    )


entries_df, skills_df, employees_df = load_all_data()

# ---- Sidebar: Employee Selection ----
st.sidebar.subheader("Employee Selection")

employees = sorted(load_csv(EMPLOYEES_FILE, ["Employee"])["Employee"].dropna().unique())
# Set selected employee from query params if available
query_params = st.query_params
default_emp = query_params.get("selected", [employees[0]])[0]
if default_emp in employees:
    selected_index = employees.index(default_emp)
else:
    selected_index = 0
selected = st.sidebar.selectbox("Select employee", employees, index=selected_index)

# ---- Add New Employee Form ----
if "show_input" not in st.session_state:
    st.session_state.show_input = False

if not st.session_state.show_input:
    if st.sidebar.button("➕ Add New Employee", key="show_input_btn"):
        st.session_state.show_input = True
        st.rerun()
else:
    new_emp = st.sidebar.text_input("Enter new employee name", key="new_employee_input")
    col1, col2 = st.sidebar.columns(2)
    submit_clicked = col1.button("Submit", key="submit_new_emp")
    cancel_clicked = col2.button("Cancel", key="cancel_new_emp")

    if cancel_clicked:
        st.session_state.show_input = False
        st.rerun()

    if submit_clicked and new_emp:
        if new_emp not in employees:
            try:
                employees_df = (
                    pd.concat(
                        [
                            load_csv(EMPLOYEES_FILE, ["Employee"]),
                            pd.DataFrame([[new_emp]], columns=["Employee"]),
                        ]
                    )
                    .drop_duplicates(subset=["Employee"])
                    .reset_index(drop=True)
                )

                save_csv(employees_df, EMPLOYEES_FILE)
                st.session_state.show_input = False
                st.query_params.update(selected=new_emp)
                st.rerun()
            except Exception as e:
                st.error(f"An error occurred while adding the employee: {e}")
        else:
            st.warning("Employee already exists.")

if not employees:
    st.sidebar.warning("No employees in database.")
    st.stop()

employee = Employee(selected, entries_df, skills_df)

# ---- Tabs ----
tabs = st.tabs(["📊 Utilization Dashboard", "📝 Submit Hours", "👥 Employee Skills"])

# ---- 📊 Utilization Dashboard ----
with tabs[0]:
    st.header("Utilization Overview")
    df = employee.entries_df

    if not df.empty:
        df_grouped = df.groupby(["Week", "Project"])["Hours"].sum().reset_index()
        st.subheader("Hours by Project")
        st.dataframe(df_grouped)

        st.subheader("Total Weekly Hours")
        df_weekly = df.groupby("Week")["Hours"].sum().reset_index()
        st.bar_chart(df_weekly.set_index("Week"))

        st.subheader("Utilization Status")
        df_util = df.groupby("Week")["Hours"].sum().reset_index()
        df_util["Status"] = df_util["Hours"].apply(
            lambda x: (
                "🟦 40h"
                if x == 40
                else ("🟩 Underutilized" if x < 40 else "🟥 Overutilized")
            )
        )
        st.dataframe(df_util.rename(columns={"Hours": "Total Hours"}))
    else:
        st.info("No data submitted yet.")

# ---- 📝 Submit Hours ----
with tabs[1]:
    st.header("Submit Your Weekly Hours")

    # Show total weekly hours across all 3 categories
    all_entries = pd.concat(
        [
            pivot_entries(employee.entries_df, "Confirmed", week_strs),
            pivot_entries(employee.entries_df, "Tentative", week_strs),
            pivot_entries(employee.entries_df, "Leave", week_strs),
        ]
    )
    total_by_week = all_entries[week_strs].sum().to_frame().T
    total_by_week.index = ["Total"]
    st.subheader("Weekly Total Hours (All Entries)")
    st.data_editor(total_by_week, disabled=True)

    st.subheader("Confirmed Projects")
    confirmed_df = st.data_editor(
        pivot_entries(employee.entries_df, "Confirmed", week_strs),
        num_rows="dynamic",
        key="confirmed",
    )

    st.subheader("Tentative Projects")
    tentative_df = st.data_editor(
        pivot_entries(employee.entries_df, "Tentative", week_strs),
        num_rows="dynamic",
        key="tentative",
    )

    st.subheader("Leave / Vacation")
    leave_df = st.data_editor(
        pivot_entries(employee.entries_df, "Leave", week_strs),
        num_rows="dynamic",
        key="leave",
    )

    # --- Rerun on edit ---
    # Streamlit's data_editor reruns the script on cell edit (cursor exit), so the summed row will update automatically.

    if st.button("💾 Save All Entries"):
        # update/overwrite existing dates (person/week = unique)
        # update the summed hours on top!
        new_entries = []
        new_entries += employee.save_entries(confirmed_df, "Confirmed", week_strs)
        new_entries += employee.save_entries(tentative_df, "Tentative", week_strs)
        new_entries += employee.save_entries(leave_df, "Leave", week_strs)

        # Append only new entries instead of overwriting
        new_data_df = pd.DataFrame(new_entries)
        existing_df = load_csv(
            ENTRIES_FILE, ["Employee", "Week", "Project", "Hours", "Status"]
        )
        combined_df = pd.concat([existing_df, new_data_df], ignore_index=True)
        save_csv(combined_df, ENTRIES_FILE)
        st.success("Entries saved!")

# ---- 👥 Skills ----
with tabs[2]:
    st.header("Employee Skills Matrix")

    with st.expander("Add Skill Entry"):
        with st.form("skills_form"):
            skill = st.text_input("Skill")
            level = st.selectbox("Skill Level", ["Beginner", "Intermediate", "Expert"])
            skill_submit = st.form_submit_button("Add Skill")
            if skill_submit:
                new_row = pd.DataFrame(
                    [[employee.name, skill, level]],
                    columns=["Employee", "Skill", "Level"],
                )
                skills_df = pd.concat([skills_df, new_row], ignore_index=True)
                save_csv(skills_df, SKILLS_FILE)
                st.success("Skill added!")

    emp_skills = employee.skills_df
    if not emp_skills.empty:
        st.dataframe(emp_skills)
    else:
        st.info("No skills for this employee.")
