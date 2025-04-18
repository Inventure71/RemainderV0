import tkinter as tk
from UI.components.widget_single_message import MessageBox

class ScrollableMessageArea(tk.Frame):
    def __init__(self, parent, db_manager=None):
        super().__init__(parent)

        self.db_manager = db_manager

        # Create Canvas + Scrollbar
        self.canvas = tk.Canvas(self, borderwidth=0, background="white")
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Create an inner frame inside the canvas
        self.inner_frame = tk.Frame(self.canvas, bg="white")
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        # Auto-resize scroll region
        self.inner_frame.bind("<Configure>", self.on_frame_configure)

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def add_message(self, text, message_id=0, assigned_project=None, project_list=None, alignment="left"):
        """
        Adds a message box to the scrollable area.

        Args:
            text (str): The message content.
            message_id (int): The ID of the message in the database.
            assigned_project (str, optional): The project assigned to the message. Defaults to None.
            project_list (list, optional): The list of available projects. Defaults to None.
            alignment (str): The horizontal alignment of the message box ('left' or 'right'). Defaults to 'left'.
        """
        message_box = MessageBox(
            self.inner_frame,
            text=text,
            db_manager=self.db_manager,
            id_of_message=message_id,
            assigned_project=assigned_project,
            project_list=project_list
        )

        # Determine packing options based on alignment
        if alignment == "right":
            # Pack to the right side (East)
            message_box.pack(fill="x", padx=(50, 10), pady=5, anchor='e')  # Add left padding to push it right
        else:  # Default to left alignment
            # Pack to the left side (West)
            message_box.pack(fill="x", padx=(10, 50), pady=5, anchor='w')  # Add right padding

        # Scroll to the bottom after adding a message (optional)
        self.canvas.update_idletasks()  # Ensure layout is updated
        self.canvas.yview_moveto(1.0)  # Move scrollbar to the end
