import time
import tkinter as tk
from tkinter import simpledialog, colorchooser
# Remove TopBar import here, it's handled by the parent
# from UI.components.widget_top_nav_bar import TopBar
from UI.components.scrollable_messages_box import ScrollableMessageArea

from DatabaseUtils.database_messages import MessageDatabaseHandler
from DatabaseUtils.database_projects import ProjectsDatabaseHandler
from UI.window_main_chat import MainChatWindow
# WidgetModelChat is implicitly used via the parent class

class ProjectChatWindow(MainChatWindow):
    def __init__(self, parent, controller, project_dictionary=None):
        self.project_dictionary = project_dictionary
        self.messages = None
        self.p_database = ProjectsDatabaseHandler()

        # --- Call Parent __init__ FIRST ---
        # This sets up the basic 2-column grid, TopBar, input_frame, model_chat etc.
        super().__init__(parent, controller)

        # --- Configure Grid Rows for THIS Window's Layout ---
        # Row 0: TopBar (handled by parent)
        # Row 1: Project Info Bar (in column 0)
        # Row 2: Project Chat Area (in column 0)
        # Row 3: Input Bar (in column 0)
        # Column 0: Left side content (Info, Chat, Input)
        # Column 10: Right side content (Model Chat - handled by parent)

        self.grid_rowconfigure(1, weight=0)  # Info bar - no vertical stretch
        self.grid_rowconfigure(2, weight=1)  # Project chat - allow vertical stretch
        self.grid_rowconfigure(3, weight=0)  # Input bar - no vertical stretch
        # Column weights (0 and 10) are already set by the parent

        # --- Project Info Bar ---
        # Placed in row 1, only in the left column (column 0)
        self.info_frame = tk.Frame(self, bg="#f4f4f4", pady=4) # Reduced padding slightly
        self.info_frame.grid(row=1, column=0, sticky="ew")
        # Configure columns *within* the info_frame
        self.info_frame.columnconfigure(0, weight=1) # Spacer
        self.info_frame.columnconfigure(1, weight=1) # Description label column

        self.desc_label = tk.Label(
            self.info_frame,
            text="",
            bg="#f4f4f4",
            anchor="w",
            justify="left",
            wraplength=1  # Real value set on resize
        )
        self.desc_label.grid(row=0, column=1, sticky="ew", pady=0)

        # Bind resize event to the main window frame for better wrap updates
        self.bind("<Configure>", self._update_desc_wrap)
        # Initial wrap update after widgets are drawn
        self.after_idle(self._update_desc_wrap)

        self.edit_desc_btn = tk.Button(self.info_frame, text="Edit Description", command=self.edit_description)
        self.edit_desc_btn.grid(row=0, column=2, sticky="e", padx=5, pady=0)

        self.edit_color_btn = tk.Button(self.info_frame, text="Edit Color", command=self.edit_color)
        self.edit_color_btn.grid(row=0, column=3, sticky="e", padx=5, pady=0)

        # --- Project Chat Area ---
        # Will be populated by populate_chat_area, which now correctly grids it
        # at row=2, column=0. Need to ensure self.scrollable_area is managed.
        # self.scrollable_area = None # Initialize perhaps

        # --- Input Bar ---
        # Re-grid the input_frame created by the parent class to the correct row
        self.input_frame.grid(row=3, column=0, sticky="ew") # Moved to row 3

        # --- Initial State ---
        self.update_project_info()
        # Populate chat based on current project (might be None initially)
        self.change_project(self.project_dictionary)


    def _update_desc_wrap(self, event=None):
        """
        Adjust the description label’s wrap length based on available space
        in the info_frame, accounting for buttons.
        """
        if not self.info_frame.winfo_exists(): # Prevent errors during teardown
             return
        # Wait for widgets inside info_frame to get their size
        self.info_frame.update_idletasks()
        button_width = 0
        if self.edit_desc_btn.winfo_exists():
            button_width += self.edit_desc_btn.winfo_width()
        if self.edit_color_btn.winfo_exists():
            button_width += self.edit_color_btn.winfo_width()

        # Estimate padding and spacing around buttons
        button_padding = 30 # Adjust as needed

        # Calculate available width for the description label
        available_width = self.info_frame.winfo_width() - button_width - button_padding
        # Ensure a minimum width to avoid errors or extreme wrapping
        available_width = max(available_width, 50)

        self.desc_label.config(wraplength=available_width)

    def refresh(self):
        # When refreshing, ensure the correct project's data is shown
        self.change_project(self.project_dictionary) # Reload messages for current project
        if hasattr(self, "desc_label"): # Ensure UI elements exist
            self.update_project_info()
        # The parent refresh might load main chat messages, which we don't want displayed here.
        # self.populate_chat_area handles displaying the correct project messages.

    def send_message(self, project_name=None):
        # Send message specifically for the current project
        if self.project_dictionary:
            # Use the parent's send_message, but force the project name
            super().send_message(project_name=self.project_dictionary["name"])
            # Refresh chat area immediately after sending
            self.messages = self.message_db.get_project_messages(self.project_dictionary["name"])
            self.populate_chat_area(self.messages)
        else:
            print("Error: No project selected to send message to.")
            # Optionally show a message to the user via messagebox or status bar

    def change_project(self, project_dictionary):
        self.project_dictionary = project_dictionary
        # Fetch and display messages for the *new* project
        if project_dictionary:
            self.messages = self.message_db.get_project_messages(self.project_dictionary["name"])
            self.populate_chat_area(self.messages)
        else:
            # Handle case where no project is selected (e.g., show a placeholder)
            self.messages = []
            self.populate_chat_area(self.messages) # Show empty or placeholder

        # Update the info bar for the new project
        if hasattr(self, "desc_label"): # Check if UI elements are created
            self.update_project_info()

    def populate_chat_area(self, messages):
        """Populate the chat area with messages FOR THE CURRENT PROJECT"""
        # Destroy the previous scrollable area if it exists to avoid stacking widgets
        if hasattr(self, 'scrollable_area') and self.scrollable_area.winfo_exists():
            self.scrollable_area.destroy()

        # Create and grid the scrollable area specifically for project chat
        self.scrollable_area = ScrollableMessageArea(self, db_manager=self.message_db)
        # *** Grid it in the correct row/column for ProjectChatWindow ***
        self.scrollable_area.grid(row=2, column=0, sticky="nsew")

        # Populate with messages or placeholder
        if self.project_dictionary and messages:
            # Get project list for message boxes (if needed for dropdown)
            all_projects = self.p_database.get_all_projects()
            project_names = [p['name'] for p in all_projects] # Example if needed

            for message in messages:
                # Ensure message has an ID, provide default if missing (though DB should handle this)
                msg_id = message.get("id", 0)
                self.scrollable_area.add_message(
                    message['content'],
                    message_id=msg_id,
                    assigned_project=message.get('project'),
                    project_list=project_names # Pass project list if needed by MessageBox
                )
        else:
            # Display a placeholder if no project is selected or no messages exist
            placeholder_text = "No Project Selected" if not self.project_dictionary else "No messages in this project yet."
            # You might want a more visually distinct placeholder than a standard message box
            placeholder_label = tk.Label(self.scrollable_area.inner_frame, text=placeholder_text, bg="white", fg="grey")
            placeholder_label.pack(pady=20)
            # self.scrollable_area.add_message(placeholder_text, message_id=-1) # Using add_message might format it undesirably


    def update_project_info(self):
        # Guard against calls before UI elements are ready
        if not hasattr(self, "desc_label") or not self.desc_label.winfo_exists():
            return
        if self.project_dictionary:
            desc = self.project_dictionary.get("description", "No description provided.")
            color = self.project_dictionary.get("color", "#f0f0f0") # Use a default neutral color
            self.desc_label.config(text=f"Description: {desc}", bg=color)
            self.info_frame.config(bg=color)
            # Update label background as well if needed
            for widget in self.info_frame.winfo_children():
                 if isinstance(widget, tk.Label): # Only change labels, not buttons
                     widget.config(bg=color)
        else:
            self.desc_label.config(text="No Project Selected", bg="#f4f4f4")
            self.info_frame.config(bg="#f4f4f4")
            for widget in self.info_frame.winfo_children():
                 if isinstance(widget, tk.Label):
                     widget.config(bg="#f4f4f4")

    def edit_description(self):
        if not self.project_dictionary:
            return
        current_desc = self.project_dictionary.get("description", "")
        new_desc = simpledialog.askstring("Edit Description", "Enter new description:", initialvalue=current_desc, parent=self) # Add parent
        if new_desc is not None: # Check if user cancelled
            self.p_database.update_project(self.project_dictionary["id"], new_description=new_desc)
            self.project_dictionary["description"] = new_desc # Update local dictionary
            self.update_project_info() # Refresh UI

    def edit_color(self):
        if not self.project_dictionary:
            return
        current_color = self.project_dictionary.get("color", "#f0f0f0")
        # askcolor returns a tuple (rgb_tuple, hex_string) or (None, None) if cancelled
        result = colorchooser.askcolor(title="Choose Project Color", initialcolor=current_color, parent=self) # Add parent
        color_code = result[1] # Get the hex string part
        if color_code: # Check if a color was chosen (hex string is not None)
            self.p_database.update_project(self.project_dictionary["id"], color=color_code)
            self.project_dictionary["color"] = color_code # Update local dictionary
            self.update_project_info() # Refresh UI
