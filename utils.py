import streamlit as st
import os, sys
import pandas as pd
import numpy as np
import hashlib


def load_csv(file, columns):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file)
            for col in columns:
                if col not in df.columns:
                    df[col] = None
            return df[columns]
        except pd.errors.EmptyDataError:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)


def save_csv(df, file):
    df.to_csv(file, index=False)


def pivot_entries(df, status, weeks):
    """
    Pivots and aggregates hours for a given status and set of weeks.

    Parameters:
        df (pd.DataFrame): Input DataFrame containing at least 'Status', 'Project', 'Week', and 'Hours' columns.
        status (str): The status value to filter the DataFrame by.
        weeks (list): List of week identifiers (column values) to include in the pivoted output.

    Returns:
        pd.DataFrame: A DataFrame with 'Project' as rows and specified weeks as columns, containing the sum of 'Hours' for each project and week.
                      If no data matches the status, returns an empty DataFrame with the appropriate columns.
    """
    filtered = df[df["Status"] == status]
    pivot = filtered.pivot_table(
        index="Project", columns="Week", values="Hours", aggfunc="sum"
    ).reset_index()
    for week in weeks:
        if week not in pivot.columns:
            pivot[week] = 0
    # Preserve the original order of "Project" as in the filtered DataFrame
    pivot = (
        pivot.set_index("Project").reindex(filtered["Project"].unique()).reset_index()
    )
    pivot["Project"] = pivot["Project"].astype(str)  # Ensure "Project" column is string
    return (
        pivot[["Project"] + weeks]
        if not pivot.empty
        else pd.DataFrame(columns=["Project"] + weeks)
    )


def styled_subheader(text, size=18, color="#dedede", margin=10, padding=0):
    st.markdown(
        f"<h3 style='font-size:{size}px; color:{color}; margin:{margin}px; padding:{padding}px;'>{text}</h3>",
        unsafe_allow_html=True,
    )


def hash_df(df):
    return hashlib.md5(pd.util.hash_pandas_object(df, index=True).values).hexdigest()


# --- Summed Hours Row ---
def sum_hours(df, weeks):
    # print(type(df))
    # sys.exit(0)
    # Only sum numeric columns (the week columns)
    week_cols = [col for col in df.columns if col in weeks]
    return df[week_cols].replace(np.nan, 0).astype(float).sum(axis=0)
