import pandas as pd


class Employee:
    """
    Employee with associated project entries, skills, office, and weekly hours.
    Attributes:
        name (str): The name of the employee.
        entries_df (pd.DataFrame): DataFrame containing project entries for the employee.
        skills_df (pd.DataFrame): DataFrame containing skills for the employee.
        office (str): The office location of the employee.
        weekly_hours (float): The weekly working hours of the employee.
    Methods:
        get_entries_by_status(status):
            Returns a DataFrame of the employee's entries filtered by the given status.
        save_entries(df, status, weeks):
            Generates a list of records for the employee based on the provided DataFrame,
            status, and list of weeks. Each record contains employee name, project, week,
            hours, and status.
    """

    def __init__(self, name, entries_df, skills_df, employee_df):
        self.name = name
        self.entries_df = entries_df[entries_df["Name"] == name].copy()
        self.skills_df = skills_df[skills_df["Name"] == name].copy()
        self.office = employee_df.loc[employee_df["Name"] == name, "Office"].values[0]
        self.weekly_hours = employee_df.loc[
            employee_df["Name"] == name, "WeeklyHours"
        ].values[0]

    def get_entries_by_status(self, status):
        return self.entries_df[self.entries_df["Status"] == status]

    def save_entries(
        self, df: pd.DataFrame, status: str, weeks: list[str]
    ) -> pd.DataFrame:
        """
        Replaces the current employee's entries for the given status with the provided DataFrame.

        Args:
            df (pd.DataFrame): Edited table to store
            status (str): One of ['Confirmed', 'Tentative', 'Leave'].
            weeks (list[str]): List of week strings.

        Returns:
            pd.DataFrame: Updated `self.entries_df`.
        """
        if df.empty:
            return self.entries_df

        # Drop current entries of this status
        self.entries_df = self.entries_df[self.entries_df["Status"] != status]

        # Convert the pivoted table into long-form records
        new_rows = []
        for _, row in df.iterrows():
            project = row.get("Project") or row.get("Type", "")
            for week in weeks:
                hours = row.get(week)
                if pd.isna(hours):
                    continue
                new_rows.append(
                    {
                        "Name": self.name,
                        "Row": row.name,
                        "Project": project,
                        "Week": week,
                        "Hours": float(hours),
                        "Status": status,
                    }
                )

        # Append new records
        self.entries_df = pd.concat(
            [self.entries_df, pd.DataFrame(new_rows)], ignore_index=True
        )
        return self.entries_df

    def save_skills(self, df_skills, category):
        """
        Save or update skills in the employee's skill DataFrame for a given category.

        Args:
            df_skills (pd.DataFrame): Skills to save, must have "Skill" and "Level".
            category (str): The skill category to which these skills belong.

        Returns:
            pd.DataFrame: The updated skills DataFrame.
        """
        df_skills = df_skills.copy()
        df_skills["Name"] = self.name
        df_skills["Category"] = category
        # df_skills["LastUpdated"] = pd.Timestamp.today().strftime("%Y-%m-%d")

        # Drop existing skills for this employee/category to avoid duplication
        mask = (self.skills_df["Name"] == self.name) & (
            self.skills_df["Category"] == category
        )
        self.skills_df = self.skills_df[~mask]

        # Append new/updated skills
        self.skills_df = pd.concat([self.skills_df, df_skills], ignore_index=True)

        # Return the updated skills DataFrame for the updated category
        return self.skills_df[self.skills_df["Category"] == category]
