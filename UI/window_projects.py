import time
import tkinter as tk

from UI.components.scrollable_box_w_clickable_projects import ScrollableBox
from UI.components.widget_top_nav_bar import TopBar

from DatabaseUtils.database_projects import ProjectsDatabaseHandler


# --- Second Menu Frame ---
class ProjectsWindow(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        self.p_database = ProjectsDatabaseHandler()
        self.controller = controller

        # Create the top bar
        TopBar(self, controller)

        tk.Label(self, text="Projects").pack(side="left", padx=5)

        # --- Top Frame: Category Selector ---
        top_frame = tk.Frame(self, pady=10)
        top_frame.pack(fill="x")

        scrollable = ScrollableBox(self, box_count=20, on_click_callback=self.handle_box_click)
        scrollable.pack(fill="both", expand=True, padx=10, pady=10)

        # Name of the new project
        input_frame = tk.Frame(self, bg="lightgray", padx=10, pady=10)
        input_frame.pack(fill="x", side="bottom")

        tk.Label(input_frame, text="New Project Name:", bg="lightgray").pack(side="left", padx=5)

        self.new_project_entry = tk.Entry(input_frame, width=30)
        self.new_project_entry.pack(side="left", padx=5)

        create_button = tk.Button(input_frame, text="Create Project",
                                  command=self.create_new_project_from_entry)
        create_button.pack(side="left", padx=5)

    def handle_box_click(self, index):
        print(f"You clicked box #{index + 1}")

    def create_new_project(self, project_name):
        self.p_database.add_project(project_name, time.time())

    def create_new_project_from_entry(self):
        project_name = self.new_project_entry.get().strip()
        if project_name:
            self.create_new_project(project_name)
            self.new_project_entry.delete(0, tk.END)  # Clear the entry field
            # You might want to refresh the project list here
