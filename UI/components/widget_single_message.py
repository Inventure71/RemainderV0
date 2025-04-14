import tkinter as tk

from DatabaseUtils.database_projects import ProjectsDatabaseHandler


class MessageBox(tk.Frame):
    def __init__(self, parent, text, db_manager=None, id_of_message=0, assigned_project=None, project_list=None, **kwargs):
        super().__init__(parent, padx=10, pady=10, bd=1, relief="solid", bg="white", **kwargs)

        """VAIRABLES"""
        self.should_be_deleted = False
        self.is_edited = False
        self.identity_in_database = None

        self.id_of_message = id_of_message
        self.db_manager = db_manager

        if project_list is None:
            project_list = []

        self.project_list = project_list
        self.assigned_project = assigned_project

        # --- Layout container to help spacing ---
        content_frame = tk.Frame(self, bg="white")
        content_frame.pack(fill="both", expand=True)

        # --- Right side: Dropdown Menu Button ---
        self.menu_button = tk.Menubutton(content_frame, text="⋮", relief="flat", bg="white", anchor="e")
        self.menu_button.pack(side="right", padx=(5, 0))

        self.menu = tk.Menu(self.menu_button, tearoff=0)
        self.menu_button.config(menu=self.menu)

        # Submenu for adding to a project
        self.add_project_menu = tk.Menu(self.menu, tearoff=0)
        for project in project_list:
            self.add_project_menu.add_command(label=project, command=lambda p=project: self.add_to_project(p))
        self.menu.add_cascade(label="Add to project", menu=self.add_project_menu)

        # Option to remove from project
        if self.assigned_project:
            self.menu.add_command(label="Remove from project", command=self.remove_from_project)

        # Edit / Delete options
        self.menu.add_command(label="Edit message", command=self.edit_message)
        self.menu.add_command(label="Delete message", command=self.delete_message)

        # --- Middle: Project Flag ---
        flag_text = self.assigned_project[:3].upper() if self.assigned_project else ""
        self.flag_label = tk.Label(content_frame, text=flag_text, foreground="black", bg="white", font=("Arial", 10, "bold"), width=4)
        self.flag_label.pack(side="right", padx=5)

        # --- Left: Wrapped Text ---
        self.message_label = tk.Label(
            content_frame,
            text=text,
            wraplength=450,  # Slightly reduced to allow space for right-side controls
            justify="left",
            anchor="w",
            foreground="black",
            bg="white",
            font=("Arial", 12)
        )
        self.message_label.pack(side="left", fill="both", expand=True, padx=(0, 10))  # Add space from right

        self.refresh_project_list()

    def refresh_project_list(self):
        self.project_list = ProjectsDatabaseHandler().get_all_projects()

        self.add_project_menu = tk.Menu(self.menu, tearoff=0)
        for project in self.project_list:
            self.add_project_menu.add_command(label=project['name'][:10], command=lambda p=project['name']: self.add_to_project(p))
        self.menu.delete(0)
        self.menu.insert_cascade(index=0, label="Add to project", menu=self.add_project_menu)

    def add_to_project(self, project_name):
        print(f"Adding message to project: {project_name} (TO IMPLEMENT)")
        self.assigned_project = project_name
        self.db_manager.update_message(self.id_of_message, project=project_name)
        self.flag_label.config(text=project_name[:3].upper())

    def remove_from_project(self):
        print("Removed from project (TO IMPLEMENT)")
        self.assigned_project = None
        self.db_manager.update_message(self.id_of_message, project="")
        self.flag_label.config(text="")

    def edit_message(self):
        print("Editing message (TO IMPLEMENT)")

    def delete_message(self):
        print("Deleting message (TO IMPLEMENT)")
        self.db_manager.delete_message(self.id_of_message)
        self.should_be_deleted = True
        self.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("MessageBox Example")
    root.geometry("600x400")

    sample_text = (
        "This is a long message that should wrap into multiple lines and grow the widget vertically. "
        "If the message is long enough, the height increases and nothing should get visually cut off."
    )
    projects = ["Project Alpha", "BetaTeam", "Notes"]

    # Create sample boxes
    box1 = MessageBox(root, text=sample_text, assigned_project="BetaTeam", project_list=projects)
    box1.pack(fill="x", padx=10, pady=5)

    box2 = MessageBox(root, text=sample_text, assigned_project=None, project_list=projects)
    box2.pack(fill="x", padx=10, pady=5)

    box3 = MessageBox(root, text=sample_text, assigned_project="Notes", project_list=projects)
    box3.pack(fill="x", padx=10, pady=5)

    root.mainloop()
