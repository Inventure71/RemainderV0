import time
import tkinter as tk
from datetime import datetime

from UI.components.scrollable_box_w_clickable_projects import ScrollableBox
from UI.components.widget_top_nav_bar import TopBar

from DatabaseUtils.database_projects import ProjectsDatabaseHandler


# --- Second Menu Frame ---
class ProjectsWindow(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        self.p_database = ProjectsDatabaseHandler()
        self.controller = controller
        self.projects = None # initialize the variable

        # Create the top bar
        TopBar(self, controller)

        tk.Label(self, text="Projects").pack(side="top", padx=5)

        # --- Top Frame: Category Selector ---
        top_frame = tk.Frame(self, pady=10)
        top_frame.pack(fill="x")

        self.scrollable = ScrollableBox(self, project_dictionary=self.projects, on_click_callback=self.clicked_project_folder)
        self.scrollable.pack(fill="both", expand=True, padx=10, pady=10)

        self.refresh()

        # Name of the new project
        input_frame = tk.Frame(self, bg="lightgray", padx=10, pady=10)
        input_frame.pack(fill="x", side="bottom")

        tk.Label(input_frame, text="New Project Name:", bg="lightgray").pack(side="left", padx=5)

        self.new_project_entry = tk.Entry(input_frame, width=30)
        self.new_project_entry.pack(side="left", padx=5)

        # Color picker for project color
        tk.Label(input_frame, text="Color:", bg="lightgray").pack(side="left", padx=5)
        self.color_entry = tk.Entry(input_frame, width=10)
        self.color_entry.insert(0, "#dddddd")
        self.color_entry.pack(side="left", padx=5)

        create_button = tk.Button(input_frame, text="Create Project",
                                  command=self.create_new_project_from_entry)
        create_button.pack(side="left", padx=5)

    def refresh(self):
        # --- Load Messages from Database ---
        self.projects = self.p_database.get_all_projects()
        self.scrollable.update_projects(projects_dictionary=self.projects)

        return self.projects

    def refresh_projects(self):
        self.projects = self.p_database.get_all_projects()
        return self.projects

    def clicked_project_folder(self, index):
        print(f"You clicked box #{index + 1}")
        print(self.projects[index])
        self.controller.select_project(self.projects[index])

    def create_new_project(self, project_name):
        self.p_database.add_project(project_name, datetime.now())
        self.refresh()

    def create_new_project_from_entry(self):
        name = self.new_project_entry.get().strip()
        color = self.color_entry.get().strip()
        if name:
            timestamp = str(datetime.now())
            self.p_database.add_project(name, timestamp, color=color, user_created=1)
            self.refresh()
            self.new_project_entry.delete(0, 'end')
            self.color_entry.delete(0, 'end')
            self.color_entry.insert(0, "#dddddd")
