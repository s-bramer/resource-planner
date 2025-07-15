import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
from utils import *
from models import Employee
import numpy as np
import altair as alt

# ---- Initialize App ----
st.set_page_config(page_title="Resource Planner", layout="wide")

# ---- CONSTANTS ----
ENTRIES_FILE = "data/entries.csv"
SKILLS_FILE = "data/skills.csv"
EMPLOYEES_FILE = "data/employees.csv"
DEFAULT_LEAVE_TYPES = ["Vacation", "Holiday", "Sick Leave"]

# ---- Precompute Weeks ----
# Find the most recent Monday (start of current week)
today = date.today()
start_monday = today - timedelta(days=today.weekday())
# Start from 2 weeks back
start_date = start_monday - timedelta(weeks=2)
week_dates = [start_date + timedelta(weeks=i) for i in range(12)]
week_strs = [w.strftime("%d-%b") for w in week_dates]
# print(f"Weeks: {week_strs}")


# ---- Cached Data Load ----
# @st.cache_data
def load_all_data():
    return (
        load_csv(ENTRIES_FILE, ["Employee", "Week", "Project", "Hours", "Status"]),
        load_csv(SKILLS_FILE, ["Employee", "Skill", "Level"]),
        load_csv(EMPLOYEES_FILE, ["Employee"]),
    )


# print("Loading all data...")
df_all_entries, df_all_skills, df_all_employees = load_all_data()

# ---- Sidebar: Employee Selection ----
st.sidebar.title("Resource Planner")
st.sidebar.subheader("Employee Selection")

employees = sorted(load_csv(EMPLOYEES_FILE, ["Employee"])["Employee"].dropna().unique())

# Determine default employee: new employee > selected employee > query params > first employee
if "new_emp_to_select" in st.session_state:
    st.query_params.update(selected=st.session_state.new_emp_to_select)
    default_emp = st.session_state.new_emp_to_select
    del st.session_state.new_emp_to_select

elif (
    "selected_employee" in st.session_state
    and st.session_state.selected_employee in employees
):
    default_emp = st.session_state.selected_employee
else:
    query_params = st.query_params
    default_emp = query_params.get("selected", [employees[0]])[0]

if default_emp in employees:
    selected_index = employees.index(default_emp)
else:
    selected_index = 0
print(f"default_emp: {default_emp}")


# on dropdown change, update query params and reload data
def on_employee_change():
    st.query_params.update(selected=st.session_state.selected_employee)
    # Clear cached data to reload
    st.cache_data.clear()
    # Reload all data
    df_all_entries, df_all_skills, df_all_employees = load_all_data()
    employee = Employee(selected, df_all_entries, df_all_skills)
    # Reset hash states to ensure fresh tracking per employee
    for key in ["confirmed_hash", "tentative_hash", "leave_hash"]:
        if key in st.session_state:
            del st.session_state[key]


# dropdown for employee selection
selected = st.sidebar.selectbox(
    "Select employee",
    employees,
    index=selected_index,
    key="selected_employee",
    on_change=on_employee_change,
)
#################################
# ---- Add New Employee Form ----
#################################
if "show_input" not in st.session_state:
    st.session_state.show_input = False

if not st.session_state.show_input:
    if st.sidebar.button("➕ Add New Employee", key="show_input_btn"):
        st.session_state.show_input = True
        # rerun entire app to show input field
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
                df_employees = (
                    pd.concat(
                        [
                            load_csv(EMPLOYEES_FILE, ["Employee"]),
                            pd.DataFrame([[new_emp]], columns=["Employee"]),
                        ]
                    )
                    .drop_duplicates(subset=["Employee"])
                    .reset_index(drop=True)
                )
                # Save the updated employees DataFrame
                save_csv(df_employees, EMPLOYEES_FILE)

                # Add default leave types for the new employee
                new_rows = []
                for leave_type in DEFAULT_LEAVE_TYPES:
                    for week in week_strs:
                        new_rows.append(
                            {
                                "Employee": new_emp,
                                "Week": week,
                                "Project": leave_type,
                                "Hours": 0,
                                "Status": "Leave",
                            }
                        )
                # Save the updated employees DataFrame
                df_all_entries = pd.concat(
                    [df_all_entries, pd.DataFrame(new_rows)], ignore_index=True
                )
                save_csv(df_all_entries, ENTRIES_FILE)

                st.session_state.show_input = False
                st.query_params.update(selected=new_emp)
                st.session_state.new_emp_to_select = new_emp
                st.rerun()
            except Exception as e:
                st.error(f"An error occurred while adding the employee: {e}")
        else:
            st.warning("Employee already exists.")

if not employees:
    st.sidebar.warning("No employees in database.")
    st.stop()

if st.sidebar.button("🔄 Clear Cache & Reload"):
    st.cache_data.clear()


employee = Employee(selected, df_all_entries, df_all_skills)
st.subheader(f"User: {employee.name}")
# print(f"Selected employee: {employee.name}")
# print(f"Employee entries: {employee.entries_df}")


# ---- Tabs ----
# tabs = st.tabs(["📊 Utilization Dashboard", "📝 Submit Hours", "👥 Employee Skills"])
tabs = st.tabs(["Time Planner", "Dashboard"])


######################
# -- TIME PLANNER -- #
######################
with tabs[0]:
    # st.header("Submit Your Weekly Hours")

    ###############
    # TOTAL HOURS #
    ###############
    total_container = st.empty()
    entry_dfs = [
        pivot_entries(employee.entries_df, "Confirmed", week_strs),
        pivot_entries(employee.entries_df, "Tentative", week_strs),
        pivot_entries(employee.entries_df, "Leave", week_strs),
    ]
    non_empty_entry_dfs = [df for df in entry_dfs if not df.empty]
    if non_empty_entry_dfs:
        all_entries = pd.concat(non_empty_entry_dfs)
    else:
        all_entries = pd.DataFrame([np.zeros(len(week_strs))], columns=week_strs)
    total_by_week = all_entries[week_strs].sum().to_frame().T
    total_by_week.insert(0, "Type", " Total Hours")
    total_by_week.index = [""] * len(total_by_week)
    total_container.data_editor(
        total_by_week,
        disabled=True,
        hide_index=True,
        column_config={
            "Type": st.column_config.TextColumn(label="Type", width="medium")
        },
    )
    ######################
    # CONFIRMED PROJECTS #
    ######################
    styled_subheader("Confirmed Projects")
    # Load and pivot Confirmed entries
    confirmed_df = pivot_entries(employee.entries_df, "Confirmed", week_strs)
    if "confirmed_hash" not in st.session_state:
        st.session_state["confirmed_hash"] = hash_df(confirmed_df)

    edited_confirmed = st.data_editor(
        confirmed_df,
        num_rows="dynamic",
        key="confirmed",
        column_config={"Project": st.column_config.TextColumn(width="medium")},
        hide_index=True,
        use_container_width=True,
    )

    new_hash = hash_df(edited_confirmed)
    if new_hash != st.session_state["confirmed_hash"]:
        updated_df = employee.save_entries(edited_confirmed, "Confirmed", week_strs)
        df_all_entries = df_all_entries[df_all_entries["Employee"] != employee.name]
        df_all_entries = pd.concat([df_all_entries, updated_df], ignore_index=True)
        save_csv(df_all_entries, ENTRIES_FILE)
        st.session_state["confirmed_hash"] = new_hash
        # st.toast("Auto-saved changes to Confirmed Projects")
        st.rerun()

    ######################
    # TENTATIVE PROJECTS #
    ######################
    styled_subheader("Tentative Projects")
    tentative_df = pivot_entries(employee.entries_df, "Tentative", week_strs)
    if "tentative_hash" not in st.session_state:
        st.session_state["tentative_hash"] = hash_df(tentative_df)

    edited_tentative = st.data_editor(
        tentative_df,
        num_rows="dynamic",
        key="tentative",
        column_config={"Project": st.column_config.TextColumn(width="medium")},
        hide_index=True,
    )

    new_hash = hash_df(edited_tentative)
    if new_hash != st.session_state["tentative_hash"]:
        updated_df = employee.save_entries(edited_tentative, "Tentative", week_strs)
        df_all_entries = df_all_entries[df_all_entries["Employee"] != employee.name]
        df_all_entries = pd.concat([df_all_entries, updated_df], ignore_index=True)
        save_csv(df_all_entries, ENTRIES_FILE)
        st.session_state["tentative_hash"] = new_hash
        # st.toast("Auto-saved changes to Tentative Projects")
        st.rerun()

    ####################
    # Leave / Vacation #
    ####################
    styled_subheader("Leave / Vacation")
    leave_data = pivot_entries(employee.entries_df, "Leave", week_strs)
    if "Project" in leave_data.columns:
        leave_data = leave_data.rename(columns={"Project": "Type"})
    if "leave_hash" not in st.session_state:
        st.session_state["leave_hash"] = hash_df(leave_data)

    edited_leave = st.data_editor(
        leave_data,
        num_rows="dynamic",
        key="leave",
        column_order=["Type"] + week_strs,
        column_config={
            "Type": st.column_config.TextColumn(
                label="Type", width="medium", disabled=True
            )
        },
        hide_index=True,
    )

    new_hash = hash_df(edited_leave)
    if new_hash != st.session_state["leave_hash"]:
        updated_df = employee.save_entries(edited_leave, "Leave", week_strs)
        df_all_entries = df_all_entries[df_all_entries["Employee"] != employee.name]
        df_all_entries = pd.concat([df_all_entries, updated_df], ignore_index=True)
        save_csv(df_all_entries, ENTRIES_FILE)
        st.session_state["leave_hash"] = new_hash
        # st.toast("Auto-saved changes to Leave Entries")
        st.rerun()

###################
# -- DASHBOARD -- #
###################

with tabs[1]:
    # st.header("Utilization Overview")

    st.subheader("Total Weekly Hours (by Status)")

    df = employee.entries_df.copy()

    if not df.empty:
        # Group by week and status
        df_grouped = df.groupby(["Week", "Status"])["Hours"].sum().reset_index()

        # Ensure consistent week ordering
        df_grouped["Week"] = pd.Categorical(
            df_grouped["Week"], categories=week_strs, ordered=True
        )

        # Base stacked bar chart
        bar_chart = (
            alt.Chart(df_grouped)
            .mark_bar()
            .encode(
                x=alt.X("Week:O", title="Week"),
                y=alt.Y("Hours:Q", title="Total Hours", stack="zero"),
                color=alt.Color(
                    "Status:N",
                    title="Status",
                    scale=alt.Scale(
                        domain=["Confirmed", "Tentative", "Leave"],
                        range=["#9dd6fa", "#f0c4f5", "#fae996"],
                    ),
                ),
                tooltip=["Week", "Status", "Hours"],
            )
        )

        # Horizontal rule at 40h
        util_line = (
            alt.Chart(pd.DataFrame({"y": [40]}))
            .mark_rule(color="red", strokeDash=[4, 4])
            .encode(y="y:Q")
        )

        # Combine
        final_chart = (bar_chart + util_line).properties(
            width=700,
            height=400,
        )

        st.altair_chart(final_chart, use_container_width=True)
    else:
        st.info("No data submitted yet.")

    # df = employee.entries_df
    # if not df.empty:
    #     # df_grouped = df.groupby(["Week", "Project"])["Hours"].sum().reset_index()
    #     # st.subheader("Hours by Project")
    #     # st.dataframe(df_grouped)

    #     st.subheader("Total Weekly Hours")
    #     df_weekly = df.groupby("Week")["Hours"].sum().reset_index()
    #     st.bar_chart(df_weekly.set_index("Week"))

    #     st.subheader("Utilization Status")
    #     df_util = df.groupby("Week")["Hours"].sum().reset_index()
    #     df_util["Status"] = df_util["Hours"].apply(
    #         lambda x: (
    #             "🟦 40h"
    #             if x == 40
    #             else ("🟩 Underutilized" if x < 40 else "🟥 Overutilized")
    #         )
    #     )
    #     st.dataframe(df_util.rename(columns={"Hours": "Total Hours"}))
    # else:
    #     st.info("No data submitted yet.")

# if st.button("💾 Save All Entries"):
#     # Save all entries for the employee
#     current_records = len(employee.entries_df)
#     df_updated = employee.save_entries(confirmed_df, "Confirmed", week_strs)
#     df_updated = employee.save_entries(tentative_df, "Tentative", week_strs)
#     print(f"saving leave entries.. \n{leave_df}")
#     df_updated = employee.save_entries(leave_df, "Leave", week_strs)
#     updated_records = len(df_updated)
#     print(f"updated.. \n{df_updated}")

#     # Filter out current employee's entries
#     df_other_entries = df_all_entries[df_all_entries["Employee"] != employee.name]
#     # Append updated entries for current employee
#     combined_entries = pd.concat([df_other_entries, df_updated], ignore_index=True)
#     save_csv(combined_entries, ENTRIES_FILE)

#     # Clear cached data to reload
#     # load_all_data.clear()
#     # Reload all data
#     df_all_entries, df_all_skills, df_all_employees = load_all_data()

#     if current_records == updated_records:
#         st.success(f"Entries updated!")
#     else:
#         st.success(f"{updated_records - current_records} new records added.")

# # ---- 👥 Skills ----
# with tabs[2]:
#     st.header("Employee Skills Matrix")

#     with st.expander("Add Skill Entry"):
#         with st.form("skills_form"):
#             skill = st.text_input("Skill")
#             level = st.selectbox("Skill Level", ["Beginner", "Intermediate", "Expert"])
#             skill_submit = st.form_submit_button("Add Skill")
#             if skill_submit:
#                 new_row = pd.DataFrame(
#                     [[employee.name, skill, level]],
#                     columns=["Employee", "Skill", "Level"],
#                 )
#                 skills_df = pd.concat([skills_df, new_row], ignore_index=True)
#                 save_csv(skills_df, SKILLS_FILE)
#                 st.success("Skill added!")

#     emp_skills = employee.skills_df
#     if not emp_skills.empty:
#         st.dataframe(emp_skills)
#     else:
#         st.info("No skills for this employee.")
