import pandas as pd


class Employee:
    """
    Employee with associated project entries and skills.
    Attributes:
        name (str): The name of the employee.
        entries_df (pd.DataFrame): DataFrame containing project entries for the employee.
        skills_df (pd.DataFrame): DataFrame containing skills for the employee.
    Methods:
        get_entries_by_status(status):
            Returns a DataFrame of the employee's entries filtered by the given status.
        save_entries(df, status, weeks):
            Generates a list of records for the employee based on the provided DataFrame,
            status, and list of weeks. Each record contains employee name, project, week,
            hours, and status.
    """

    def __init__(self, name, entries_df, skills_df):
        self.name = name
        self.entries_df = entries_df[entries_df["Employee"] == name].copy()
        self.skills_df = skills_df[skills_df["Employee"] == name].copy()

    def get_entries_by_status(self, status):
        return self.entries_df[self.entries_df["Status"] == status]

    def save_entries(self, df, status, weeks):
        """
        Updates the employee's entries_df DataFrame with new or updated project hour entries.

        For each row in the provided DataFrame `df` and for each week in `weeks`, this method checks if an entry
        for the employee/project/week/status combination already exists in self.entries_df. If it exists, the hours
        are updated; otherwise, a new entry is appended. The employee's entries_df is updated in-place.

        Args:
            df (pd.DataFrame): DataFrame containing at least "Project" and week columns with hour values.
            status (str): Status to assign to each record (e.g., "submitted", "approved").
            weeks (Iterable[str]): List or iterable of week identifiers (column names in `df`) to process.

        Returns:
            pd.DataFrame: The updated entries DataFrame.
        """
        for _, row in df.iterrows():
            project = row.get("Project", None)
            if project is None:
                project = row.get("Type")
            if not project:
                continue
            for week in weeks:
                hours = row.get(week, 0)
                if pd.isna(hours):
                    continue
                # Check if the entry already exists
                mask = (
                    (self.entries_df["Employee"] == self.name)
                    & (self.entries_df["Project"] == project)
                    & (self.entries_df["Week"] == week)
                    & (self.entries_df["Status"] == status)
                )
                # If it exists, update the hours; otherwise, create a new entry
                if mask.any():
                    self.entries_df.loc[mask, "Hours"] = float(hours)
                else:
                    new_row = {
                        "Employee": self.name,
                        "Project": project,
                        "Week": week,
                        "Hours": float(hours),
                        "Status": status,
                    }
                    self.entries_df = pd.concat(
                        [self.entries_df, pd.DataFrame([new_row])], ignore_index=True
                    )
        return self.entries_df
