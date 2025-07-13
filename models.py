import pandas as pd


class Employee:
    def __init__(self, name, entries_df, skills_df):
        self.name = name
        self.entries_df = entries_df[entries_df["Employee"] == name].copy()
        self.skills_df = skills_df[skills_df["Employee"] == name].copy()

    def get_entries_by_status(self, status):
        return self.entries_df[self.entries_df["Status"] == status]

    def save_entries(self, df, status, weeks):
        records = []
        for _, row in df.iterrows():
            for week in weeks:
                hours = row.get(week, 0)
                if pd.notna(hours) and row.get("Project"):
                    records.append(
                        {
                            "Employee": self.name,
                            "Project": row["Project"],
                            "Week": week,
                            "Hours": float(hours),
                            "Status": status,
                        }
                    )
        return records
