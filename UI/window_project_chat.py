# This file is deprecated. All UI logic is now handled in web/index.html and web/main.js using HTML/JS and pywebview.

# The previous Tkinter-based ProjectChatWindow is no longer used.

# You can implement any new Python-to-JS API endpoints in main.py for backend logic.

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

        # --- Create a container frame for the left side content ---
        self.left_container = tk.Frame(self, bg="#23272e")
        self.left_container.grid(row=1, column=0, rowspan=3, sticky="nsew", padx=(0, 0), pady=(0, 0))

        # Configure the left container to have three rows
        self.left_container.grid_rowconfigure(0, weight=0)  # Info frame - no vertical stretch
        self.left_container.grid_rowconfigure(1, weight=1)  # Chat area - allow vertical stretch
        self.left_container.grid_rowconfigure(2, weight=0)  # Input bar - no vertical stretch
        self.left_container.grid_columnconfigure(0, weight=1)  # Full width

        # --- Configure Grid Rows for THIS Window's Layout ---
        # Row 0: TopBar (handled by parent)
        # Row 1: Left container (contains info frame, chat area, and input bar)
        # Column 0: Left side content
        # Column 10: Right side content (Model Chat - handled by parent)

        self.grid_rowconfigure(1, weight=1)  # Left container - allow vertical stretch
        # Column weights (0 and 10) are already set by the parent

        # --- Project Info Bar ---
        # Placed in row 0 of the left container
        self.info_frame = tk.Frame(self.left_container, bg="#303441", pady=4)
        self.info_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 8))

        # Configure columns *within* the info_frame
        self.info_frame.columnconfigure(0, weight=1)  # Description label column
        self.info_frame.columnconfigure(1, weight=0)  # Buttons column - no horizontal stretch

        self.desc_label = tk.Label(
            self.info_frame,
            text="",
            bg="#303441",
            fg="black",
            anchor="w",
            justify="left",
            wraplength=1  # Real value set on resize
        )
        self.desc_label.grid(row=0, column=0, sticky="ew", pady=0)

        # Create a frame for buttons to keep them together
        self.buttons_frame = tk.Frame(self.info_frame, bg="#303441")
        self.buttons_frame.grid(row=0, column=1, sticky="e", padx=(8, 0))

        self.edit_desc_btn = tk.Button(self.buttons_frame, text="Edit Description", command=self.edit_description, bg="#2c2f33", fg="black", activebackground="#23272e", activeforeground="black")
        self.edit_desc_btn.pack(side="left", padx=5)

        self.edit_color_btn = tk.Button(self.buttons_frame, text="Edit Color", command=self.edit_color, bg="#2c2f33", fg="black", activebackground="#23272e", activeforeground="black")
        self.edit_color_btn.pack(side="left", padx=5)

        # Bind resize event to the main window frame for better wrap updates
        self.bind("<Configure>", self._update_desc_wrap)
        # Initial wrap update after widgets are drawn
        self.after_idle(self._update_desc_wrap)

        # --- Project Chat Area ---
        # Will be populated by populate_chat_area, which now correctly grids it
        # at row=1 of the left container

        # --- Input Bar ---
        # Destroy and recreate input_frame as a child of left_container for correct placement
        try:
            self.input_frame.destroy()
        except Exception:
            pass
        self.input_frame = tk.Frame(self.left_container, bg="#303441", padx=16, pady=8)
        self.input_frame.grid(row=2, column=0, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        self.message_entry = tk.Entry(self.input_frame, font=("Arial", 13), bg="#23272e", fg="#f7f7f7", insertbackground="#f7f7f7", bd=1, relief="flat", highlightthickness=1, highlightbackground="#44495a")
        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 12), pady=2)
        send_button = tk.Button(self.input_frame, text="Send", command=self.send_message, font=("Arial", 12, "bold"), bg="#3578e5", fg="black", activebackground="#2851a3", activeforeground="black", bd=0, padx=18, pady=8, relief="flat")
        send_button.grid(row=0, column=1, pady=2)

        # --- Initial State ---
        self.update_project_info()
        # Populate chat based on current project (might be None initially)
        # This will now work correctly since left_container exists
        self.change_project(self.project_dictionary)


    def _update_desc_wrap(self, event=None):
        """
        Adjust the description label’s wrap length based on available space
        in the info_frame, accounting for the button frame.
        """
        if not hasattr(self, "info_frame") or not self.info_frame.winfo_exists(): # Prevent errors during initialization or teardown
             return
        # Wait for widgets inside info_frame to get their size
        self.info_frame.update_idletasks()

        # With the new layout, we can simply use the width of the description label's cell
        # Calculate available width for the description label
        available_width = self.info_frame.winfo_width()

        # If button_frame exists and is visible, subtract its width
        if hasattr(self, 'buttons_frame') and self.buttons_frame.winfo_exists():
            button_frame_width = self.buttons_frame.winfo_width()
            # Add some padding
            button_padding = 20
            available_width -= (button_frame_width + button_padding)

        # Ensure a minimum width to avoid errors or extreme wrapping
        available_width = max(available_width, 100)

        self.desc_label.config(wraplength=available_width)

    def refresh(self):
        # When refreshing, ensure the correct project's data is shown
        # Only proceed if we have the necessary UI components
        if hasattr(self, "left_container"):
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
            # Only populate chat area if we have the necessary UI components
            if hasattr(self, "left_container"):
                self.populate_chat_area(self.messages)
        else:
            # Handle case where no project is selected (e.g., show a placeholder)
            self.messages = []
            # Only populate chat area if we have the necessary UI components
            if hasattr(self, "left_container"):
                self.populate_chat_area(self.messages) # Show empty or placeholder

        # Update the info bar for the new project
        if hasattr(self, "desc_label") and hasattr(self, "info_frame"): # Check if UI elements are created
            self.update_project_info()

    def populate_chat_area(self, messages):
        """Populate the chat area with messages FOR THE CURRENT PROJECT"""
        # Destroy the previous scrollable area if it exists to avoid stacking widgets
        if hasattr(self, 'scrollable_area') and self.scrollable_area.winfo_exists():
            self.scrollable_area.destroy()

        # Check if left_container exists yet (it might not during initial parent.__init__)
        if not hasattr(self, 'left_container'):
            # During initial setup, use self as parent temporarily
            # This will be replaced once left_container is created
            self.scrollable_area = ScrollableMessageArea(self, db_manager=self.message_db)
            self.scrollable_area.grid(row=1, column=0, sticky="nsew")
            return  # Exit early, we'll repopulate after full initialization

        # Create and grid the scrollable area specifically for project chat
        # Now place it in the left_container at row 1
        self.scrollable_area = ScrollableMessageArea(self.left_container, db_manager=self.message_db)
        self.scrollable_area.grid(row=1, column=0, sticky="nsew")

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
        if not hasattr(self, "desc_label") or not hasattr(self, "info_frame") or not self.desc_label.winfo_exists():
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
