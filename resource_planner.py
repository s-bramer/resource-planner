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
DEFAULT_BD_TYPES = ["Proposal", "Training", "Technical Development", "Conference"]

# ---- Cached Data Load ----
# @st.cache_data
def load_all_data():
    return (
        load_csv(ENTRIES_FILE, ["Name", "Row", "Week", "Project", "Hours", "Status"]),
        load_csv(SKILLS_FILE, ["Name", "Category", "Skill", "Level", "LastUpdated"]),
        load_csv(EMPLOYEES_FILE, ["Name", "Office", "WeeklyHours"]),
    )


def on_skills_change(key, category, employee, df_all_skills):
    change = st.session_state[key]
    print(f"\n🔄 Skill change detected in '{key}' (Category: {category}):")

    updated_df = df_all_skills[
        (df_all_skills["Name"] == employee.name)
        & (df_all_skills["Category"] == category)
    ].copy()
    updated_df = updated_df.reset_index(drop=True)

    changed_cells = []
    added_rows = []
    deleted_rows = change.get("deleted_rows", [])

    # --- Process edited rows ---
    for row_idx, edits in change.get("edited_rows", {}).items():
        for col, new_val in edits.items():
            # Ensure column dtype is object to accept string
            if pd.api.types.is_numeric_dtype(updated_df[col]) and isinstance(
                new_val, str
            ):
                updated_df[col] = updated_df[col].astype("object")

            old_val = updated_df.at[int(row_idx), col]
            changed_cells.append((row_idx, col, old_val, new_val))
            updated_df.at[int(row_idx), col] = new_val
            updated_df.at[int(row_idx), "LastUpdated"] = pd.Timestamp.today().strftime(
                "%Y-%m-%d"
            )

    # --- Process added rows ---
    for row in change.get("added_rows", []):
        if "Skill" not in row or "Level" not in row:
            continue
        row_data = {
            "Skill": row["Skill"],
            "Level": row["Level"],
            # "Category": category,
            # "Name": employee.name,
            "LastUpdated": pd.Timestamp.today().strftime("%Y-%m-%d"),
        }
        updated_df = pd.concat(
            [updated_df, pd.DataFrame([row_data])], ignore_index=True
        )
        added_rows.append(row_data)

    # --- Process deleted rows ---
    updated_df = updated_df.drop(index=deleted_rows).reset_index(drop=True)

    # --- Logging ---
    if changed_cells:
        print("✏️ Edited cells:")
        for idx, col, old, new in changed_cells:
            print(f"  • Row {idx}, Column '{col}': '{old}' → '{new}'")
    if added_rows:
        print("➕ Added rows:")
        for r in added_rows:
            print(f"  • {r}")
    if deleted_rows:
        print(f"🗑️ Deleted row indices: {deleted_rows}")

    # Save to employee's skills_df
    employee.skills_df = employee.save_skills(updated_df, category)
    # Remove current employee's skills in this category from global table
    df_all_skills = df_all_skills[
        ~(
            (df_all_skills["Name"] == employee.name)
            & (df_all_skills["Category"] == category)
        )
    ]
    df_all_skills = pd.concat([df_all_skills, employee.skills_df], ignore_index=True)

    # Save to file
    save_csv(df_all_skills, SKILLS_FILE)


def on_table_change(key, original_df, weeks, status, employee, df_all_entries):
    change = st.session_state[key]
    print(f"\n🔄 Change detected in '{key}':")
    # print("Session state diff:", change)

    updated_df = original_df.copy()

    # Track changes for print
    changed_cells = []
    added_rows = []
    deleted_rows = change["deleted_rows"]

    # --- Process edited rows ---
    for row_idx, edits in change["edited_rows"].items():
        for col, new_val in edits.items():
            old_val = updated_df.at[int(row_idx), col]
            changed_cells.append((row_idx, col, old_val, new_val))
            updated_df.at[int(row_idx), col] = new_val

    # --- Process added rows ---
    for row in change["added_rows"]:
        if "Project" not in row:
            continue
        new_row = {"Project": row["Project"]}
        for week in weeks:
            new_row[week] = row.get(week, 0)
        updated_df = pd.concat([updated_df, pd.DataFrame([new_row])], ignore_index=True)
        added_rows.append(new_row)

    # --- Process deleted rows ---
    updated_df = updated_df.drop(index=deleted_rows).reset_index(drop=True)

    # --- Logging changes ---
    if changed_cells:
        print("✏️ Edited cells:")
        for idx, col, old, new in changed_cells:
            print(f"  • Row {idx}, Column '{col}': '{old}' → '{new}'")
    if added_rows:
        print("➕ Added rows:")
        for r in added_rows:
            print(f"  • {r}")
    if deleted_rows:
        print(f"🗑️ Deleted row indices: {deleted_rows}")

    # changed_column = detect_changed_column(updated_df, original_df)
    # print(f"  Changes detected in column: {changed_column}")

    # Save to employee
    employee_df = employee.save_entries(updated_df, status, weeks)

    # Replace all current employee data in entries file
    df_all_entries = df_all_entries[df_all_entries["Name"] != employee.name]
    df_all_entries = pd.concat([df_all_entries, employee_df], ignore_index=True)
    save_csv(df_all_entries, ENTRIES_FILE)

    # st.toast(f"{status} data updated.")


# Load all data at the start
df_all_entries, df_all_skills, df_all_employees = load_all_data()

st.session_state["rerun_count"] = st.session_state.get("rerun_count", 0) + 1
print(f"Rerun count: {st.session_state['rerun_count']}")

#################
# -- SIDEBAR -- #
#################
with st.sidebar:
    st.image("img/logo.png", width=180)
    st.title("Resource Planner")

    employees = sorted(load_csv(EMPLOYEES_FILE, ["Name"])["Name"].dropna().unique())

    # Set default employee
    query_params = st.query_params
    default_emp = query_params.get("selected", [employees[0]])

    if "new_emp_to_select" in st.session_state:
        st.query_params.update(selected=st.session_state.new_emp_to_select)
        default_emp = st.session_state.new_emp_to_select
        del st.session_state.new_emp_to_select

    selected_index = employees.index(default_emp) if default_emp in employees else 0

    # on dropdown change, update query params and reload data
    def on_employee_change():
        st.query_params.update(selected=st.session_state.selected_employee)
        st.cache_data.clear()
        df_all_entries, df_all_skills, df_all_employees = load_all_data()

    # dropdown for employee selection
    selected = st.selectbox(
        "Select employee",
        employees,
        index=employees.index(default_emp) if default_emp in employees else 0,
        key="selected_employee",
        on_change=on_employee_change,
    )

    if "selected_employee" not in st.session_state:
        st.session_state["selected_employee"] = default_emp

    ##############
    # Week Range #
    ##############
    st.markdown("---")
    # st.subheader("Select week range to view")
    base_monday = date.today() - timedelta(days=date.today().weekday())
    min_weeks_back = 12
    max_weeks_forward = 20

    week_span = st.slider(
        "Select week range to view",
        min_value=-min_weeks_back,
        max_value=max_weeks_forward,
        value=(0, 10),
        step=1,
    )
    styled_subheader("0 = current week", size=12, margin=0, padding=3)

    start_date = base_monday + timedelta(weeks=week_span[0])
    end_date = base_monday + timedelta(weeks=week_span[1])
    week_dates = [
        start_date + timedelta(weeks=i)
        for i in range((end_date - start_date).days // 7 + 1)
    ]
    week_strs = [w.strftime("%d-%b") for w in week_dates]

    st.session_state["week_range"] = week_span
    st.session_state["week_strs"] = week_strs
    st.session_state["week_dates"] = week_dates

    #########################
    # Add New Employee Form #
    #########################
    st.markdown("---")
    # st.subheader("Add New Employee")

    if "show_input" not in st.session_state:
        st.session_state.show_input = False

    if not st.session_state.show_input:
        if st.button("➕ Add New Employee", key="show_input_btn"):
            st.session_state.show_input = True
            st.rerun()
    else:
        new_emp = st.text_input("Enter new employee name", key="new_employee_input")
        office = st.selectbox(
            "Select office location",
            options=["UK", "France", "Switzerland", "Other"],
            key="new_employee_office",
        )
        weekly_hours = st.number_input(
            "Enter weekly hours",
            key="new_employee_hours",
            step=0.5,
            value=40.0,
        )
        col1, col2 = st.columns(2)
        if (
            col1.button("Submit", key="submit_new_emp")
            and new_emp
            and office
            and weekly_hours
        ):
            if new_emp not in employees:
                df_employees = (
                    pd.concat(
                        [
                            load_csv(EMPLOYEES_FILE, ["Name", "Office", "WeeklyHours"]),
                            pd.DataFrame(
                                [[new_emp, office, weekly_hours]],
                                columns=["Name", "Office", "WeeklyHours"],
                            ),
                        ]
                    )
                    .drop_duplicates()
                    .reset_index(drop=True)
                )
                save_csv(df_employees, EMPLOYEES_FILE)

                # Add default leave and BD types for new employee
                if "week_strs" in st.session_state:
                    week_strs = st.session_state["week_strs"]
                else:
                    # Fallback (should rarely happen)
                    base_monday = date.today() - timedelta(days=date.today().weekday())
                    week_strs = [
                        (base_monday + timedelta(weeks=i)).strftime("%d-%b")
                        for i in range(12)
                    ]

                leave_rows = [
                    {
                        "Name": new_emp,
                        "Row": i,
                        "Week": week,
                        "Project": leave,
                        "Hours": 0,
                        "Status": "Leave",
                    }
                    for i, leave in enumerate(DEFAULT_LEAVE_TYPES)
                    for week in week_strs
                ]
                
                bd_rows = [
                    {
                        "Name": new_emp,
                        "Row": i,
                        "Week": week,
                        "Project": bd,
                        "Hours": 0,
                        "Status": "BD",
                    }
                    for i, bd in enumerate(DEFAULT_BD_TYPES)
                    for week in week_strs
                ]

                df_entries = load_csv(
                    ENTRIES_FILE, ["Name", "Week", "Project", "Hours", "Status"]
                )
                df_all = pd.concat(
                    [df_entries, pd.DataFrame(leave_rows), pd.DataFrame(bd_rows)], ignore_index=True
                )
                save_csv(df_all, ENTRIES_FILE)
                
                # Add default skills for new employee
                skills_template = load_csv(
                    "data/skills_template.csv", ["Category", "Skill"]
                )
                default_skills = [
                    {
                        "Name": new_emp,
                        "Category": row["Category"],
                        "Skill": row["Skill"],
                        "Level": "",
                        "LastUpdated": "",
                    }
                    for _, row in skills_template.iterrows()
                ]

                df_skills = load_csv(
                    SKILLS_FILE, ["Name", "Category", "Skill", "Level", "LastUpdated"]
                )
                df_all_skills = pd.concat(
                    [df_skills, pd.DataFrame(default_skills)], ignore_index=True
                )
                save_csv(df_all_skills, SKILLS_FILE)
                st.session_state.show_input = False
                st.session_state.new_emp_to_select = new_emp
                st.rerun()
            else:
                st.warning("Name already exists.")
        if col2.button("Cancel", key="cancel_new_emp"):
            st.session_state.show_input = False
            st.rerun()

employee = Employee(selected, df_all_entries, df_all_skills, df_all_employees)
##########
# HEADER #
##########
with st.container():
    col1, col2, col3 = st.columns([1, 10, 1])

    # Avatar
    with col1:
        st.image("img/user.png", width=90)

    # Employee details
    with col2:
        styled_subheader(employee.name, size=30, margin=0, padding=3)
        styled_subheader(
            f"Office: {employee.office}", size=15, color="#bbbbbb", margin=0, padding=3
        )
        styled_subheader(
            f"Weekly Hours: {employee.weekly_hours}",
            size=15,
            color="#bbbbbb",
            margin=0,
            padding=3,
        )
    # Help button
    with col3:
        if st.button(
            "❓Help", key="help_button", help="No help yet, you are on your own! 😅"
        ):
            pass
# print(f"Selected employee: {employee.name}")

# ---- Tabs ----
# tabs = st.tabs(["📊 Utilization Dashboard", "📝 Submit Hours", "👥 Employee Skills"])
tabs = st.tabs(["Time Planner", "Dashboard", "Skills"])


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
        pivot_entries(employee.entries_df, "Confirmed", st.session_state["week_strs"]),
        pivot_entries(employee.entries_df, "Tentative", st.session_state["week_strs"]),
        pivot_entries(employee.entries_df, "BD", st.session_state["week_strs"]),
        pivot_entries(employee.entries_df, "Leave", st.session_state["week_strs"]),
    ]
    non_empty_entry_dfs = [df for df in entry_dfs if not df.empty]
    if non_empty_entry_dfs:
        all_entries = pd.concat(non_empty_entry_dfs)
    else:
        all_entries = pd.DataFrame(
            [np.zeros(len(st.session_state["week_strs"]))],
            columns=st.session_state["week_strs"],
        )
    total_by_week = all_entries[st.session_state["week_strs"]].sum().to_frame().T
    total_by_week.insert(0, "Type", " Total Hours")
    total_by_week.index = [""] * len(total_by_week)

    # week_column_config = {
    #     week: st.column_config.BarChartColumn(
    #         label=week,
    #         help=None,
    #         y_min=0,
    #         y_max=40,
    #         width="small",
    #     )
    #     for week in week_strs
    # }

    # Add config for the first column
    column_config = {
        "Type": st.column_config.TextColumn(
            label="Type", width="medium", disabled=True
        ),
        # **week_column_config,
    }

    total_container.data_editor(
        total_by_week,
        disabled=True,
        hide_index=True,
        column_config=column_config,
    )
    ######################
    # CONFIRMED PROJECTS #
    ######################
    styled_subheader("Confirmed Projects")
    confirmed_df = pivot_entries(
        employee.entries_df, "Confirmed", st.session_state["week_strs"]
    )

    st.data_editor(
        confirmed_df,
        num_rows="dynamic",
        key="confirmed",
        on_change=on_table_change,
        args=(
            "confirmed",
            confirmed_df,
            week_strs,
            "Confirmed",
            employee,
            df_all_entries,
        ),
        column_config={"Project": st.column_config.TextColumn(width="medium")},
        hide_index=True,
        use_container_width=True,
    )

    ######################
    # TENTATIVE PROJECTS #
    ######################
    styled_subheader("Tentative Projects")
    tentative_df = pivot_entries(
        employee.entries_df, "Tentative", st.session_state["week_strs"]
    )

    st.data_editor(
        tentative_df,
        num_rows="dynamic",
        key="tentative",
        on_change=on_table_change,
        args=(
            "tentative",
            tentative_df,
            week_strs,
            "Tentative",
            employee,
            df_all_entries,
        ),
        column_config={"Project": st.column_config.TextColumn(width="medium")},
        hide_index=True,
        use_container_width=True,
    )
    
    #########################
    # Buisiness Development #
    #########################
    styled_subheader("Buisiness Development")
    bd_data = pivot_entries(
        employee.entries_df, "BD", st.session_state["week_strs"]
    )
    if "Project" in bd_data.columns:
        bd_data = bd_data.rename(columns={"Project": "Type"})

    st.data_editor(
        bd_data,
        num_rows="dynamic",
        key="bd",
        on_change=on_table_change,
        args=(
            "bd",
            bd_data,
            week_strs,
            "BD",
            employee,
            df_all_entries,
        ),
        column_config={"Type": st.column_config.TextColumn(width="medium")},
        hide_index=True,
        use_container_width=True,
    )

    ####################
    # Leave / Vacation #
    ####################
    styled_subheader("Leave / Holiday")
    leave_data = pivot_entries(
        employee.entries_df, "Leave", st.session_state["week_strs"]
    )
    if "Project" in leave_data.columns:
        leave_data = leave_data.rename(columns={"Project": "Type"})

    st.data_editor(
        leave_data,
        num_rows="dynamic",
        key="leave",
        on_change=on_table_change,
        args=(
            "leave",
            leave_data,
            week_strs,
            "Leave",
            employee,
            df_all_entries,
        ),
        column_config={"Type": st.column_config.TextColumn(width="medium")},
        hide_index=True,
        use_container_width=True,
    )

###################
# -- DASHBOARD -- #
###################

with tabs[1]:

    with st.expander("Total Weekly Hours (by Status)", expanded=False):
        # st.subheader("Total Weekly Hours (by Status)")

        df = employee.entries_df.copy()
        if df["Hours"].sum() > 0:
            # Group by week and status
            df_grouped = df.groupby(["Week", "Status"])["Hours"].sum().reset_index()

            # Convert Week to datetime for correct sorting
            df_grouped["Week_dt"] = pd.to_datetime(df_grouped["Week"], format="%d-%b")
            week_strs_sorted = sorted(
                st.session_state["week_strs"],
                key=lambda x: pd.to_datetime(x, format="%d-%b"),
            )
            df_grouped = df_grouped[df_grouped["Week"].isin(week_strs_sorted)].copy()
            df_grouped["Week"] = pd.Categorical(
                df_grouped["Week"], categories=week_strs_sorted, ordered=True
            )
            # Filter data to only include selected weeks
            min_week = st.session_state["week_strs"][0]
            max_week = st.session_state["week_strs"][-1]
            df_grouped = df_grouped[
                (df_grouped["Week"] >= min_week) & (df_grouped["Week"] <= max_week)
            ]
            # Base stacked bar chart
            bar_chart = (
                alt.Chart(df_grouped)
                .mark_bar()
                .encode(
                    x=alt.X("Week:O", title="Week", sort=week_strs_sorted),
                    y=alt.Y("Hours:Q", title="Total Hours", stack="zero"),
                    color=alt.Color(
                        "Status:N",
                        title="Status",
                        scale=alt.Scale(
                            domain=["Confirmed", "Tentative", "BD", "Leave"],
                            range=["#9dd6fa", "#f0c4f5", "#71f6cc", "#fae996"],
                        ),
                    ),
                    tooltip=["Week", "Status", "Hours"],
                )
            )

            # Horizontal rule at Weekly Hours
            util_line = (
                alt.Chart(pd.DataFrame({"y": [employee.weekly_hours]}))
                .mark_rule(color="green", strokeDash=[4, 4])
                .encode(y="y:Q")
            )

            # Combine
            final_chart = (bar_chart + util_line).properties(
                width=700,
                height=400,
            )

            st.altair_chart(final_chart, use_container_width=True)
        else:
            st.info("No hours submitted yet..")

    with st.expander(
        "Weekly Hours (as Percentage of Total Weekly Hours)", expanded=False
    ):
        # st.subheader("Weekly Hours as Percentage of Total Weekly Hours")

        if df["Hours"].sum() > 0:
            df_grouped["Percentage"] = df_grouped["Hours"] / employee.weekly_hours * 100

            percentage_chart = (
                alt.Chart(df_grouped)
                .mark_bar()
                .encode(
                    x=alt.X("Week:O", title="Week", sort=week_strs_sorted),
                    y=alt.Y(
                        "Percentage:Q", title="Percentage of Weekly Hours", stack="zero"
                    ),
                    color=alt.Color(
                        "Status:N",
                        title="Status",
                        scale=alt.Scale(
                            domain=["Confirmed", "Tentative", "BD", "Leave"],
                            range=["#9dd6fa", "#f0c4f5", "#71f6cc", "#fae996"],
                        ),
                    ),
                    tooltip=["Week", "Status", "Percentage"],
                )
            )

            percentage_line = (
                alt.Chart(pd.DataFrame({"y": [100]}))
                .mark_rule(color="green", strokeDash=[4, 4])
                .encode(y="y:Q")
            )

            final_percentage_chart = (percentage_chart + percentage_line).properties(
                width=700,
                height=400,
            )

            st.altair_chart(final_percentage_chart, use_container_width=True)
        else:
            st.info("No hours submitted yet..")

    with st.expander("Heatmap of Weekly Hours for All Employees", expanded=False):
        # Load all employee entries
        all_entries = df_all_entries.copy()
        all_entries = (
            all_entries.groupby(["Name", "Week"], observed=False)["Hours"]
            .sum()
            .reset_index()
        )

        # Convert Week to datetime for sorting
        all_entries["Week_dt"] = pd.to_datetime(all_entries["Week"], format="%d-%b")
        week_strs_sorted = sorted(
            st.session_state["week_strs"],
            key=lambda x: pd.to_datetime(x, format="%d-%b"),
        )
        all_entries["Week"] = pd.Categorical(
            all_entries["Week"], categories=week_strs_sorted, ordered=True
        )

        # Ensure unique combinations of Name and Week by aggregating
        all_entries = (
            all_entries.groupby(["Name", "Week"], observed=True)["Hours"]
            .sum()
            .reset_index()
        )

        # Pivot data for heatmap
        heatmap_data = all_entries.pivot(
            index="Name", columns="Week", values="Hours"
        ).fillna(0)

        # Convert to long format for Altair
        heatmap_long = heatmap_data.reset_index().melt(
            id_vars="Name", var_name="Week", value_name="Hours"
        )

        # Heatmap chart
        heatmap_chart = (
            alt.Chart(heatmap_long)
            .mark_rect()
            .encode(
                x=alt.X("Week:O", title="Week", sort=week_strs_sorted),
                y=alt.Y("Name:O", title="Employee"),
                color=alt.Color(
                    "Hours:Q",
                    title="Hours",
                    scale=alt.Scale(scheme="reds", domain=[0, 40]),
                ),
                tooltip=["Name", "Week", "Hours"],
            )
            .properties(width=700, height=400)
        )

        st.altair_chart(heatmap_chart, use_container_width=True)

################
# -- SKILLS -- #
################
with tabs[2]:
    with st.expander("Enter Your Skills", expanded=False):
        # Filter skills for the selected employee
        emp_skills = df_all_skills[df_all_skills["Name"] == employee.name]

        if not emp_skills.empty:

            # Get unique categories
            categories = sorted(emp_skills["Category"].unique())

            cols = st.columns(2)

            # Create a separate data_editor for each category
            for idx, category in enumerate(categories):
                col = cols[idx % 2]
                with col:
                    styled_subheader(category, size=20, margin=0, padding=5)
                    category_skills = emp_skills[emp_skills["Category"] == category][
                        ["Skill", "Level"]
                    ]

                    category_skills_clean = category_skills.copy().reset_index(
                        drop=True
                    )
                    category_skills_clean.index.name = None
                    category_skills_clean["Level"] = category_skills_clean[
                        "Level"
                    ].astype(str)
                    st.data_editor(
                        category_skills_clean,
                        column_config={
                            "Skill": st.column_config.TextColumn(),
                            "Level": st.column_config.SelectboxColumn(
                                options=["Beginner", "Intermediate", "Expert"]
                            ),
                        },
                        num_rows="dynamic",
                        key=f"skills_editor_{category}",
                        hide_index=True,
                        use_container_width=True,
                        on_change=on_skills_change,
                        args=(
                            f"skills_editor_{category}",
                            category,
                            employee,
                            df_all_skills,
                        ),
                    )
        else:
            st.info("No skills submitted yet..")

    with st.expander("Company Skills Matrix", expanded=False):
        category = st.selectbox(
            "Filter by Category", options=sorted(df_all_skills["Category"].unique())
        )
        search_skill = st.text_input("Search for a Skill")

        filtered = df_all_skills[
            df_all_skills["Category"].str.contains(category, case=False, na=False)
            & df_all_skills["Skill"].str.contains(search_skill, case=False, na=False)
        ]

        st.dataframe(
            filtered.sort_values(by=["Skill", "Level"]),
            hide_index=True,
        )
