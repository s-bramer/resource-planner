# utils.py
import os, sys
import pandas as pd
import numpy as np


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
    filtered = df[df["Status"] == status]
    pivot = filtered.pivot_table(
        index="Project", columns="Week", values="Hours", aggfunc="sum"
    ).reset_index()
    for week in weeks:
        if week not in pivot.columns:
            pivot[week] = 0
    return (
        pivot[["Project"] + weeks]
        if not pivot.empty
        else pd.DataFrame(columns=["Project"] + weeks)
    )


# --- Summed Hours Row ---
def sum_hours(df, weeks):
    # print(type(df))
    # sys.exit(0)
    # Only sum numeric columns (the week columns)
    week_cols = [col for col in df.columns if col in weeks]
    return df[week_cols].replace(np.nan, 0).astype(float).sum(axis=0)
