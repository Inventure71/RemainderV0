import tkinter as tk

from UI.components.scrollable_box_w_clickable_projects import ScrollableBox
from UI.components.widget_top_nav_bar import TopBar

# --- Second Menu Frame ---
class ProjectsWindow(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        # Create the top bar
        TopBar(self, controller)

        tk.Label(self, text="Projects").pack(side="left", padx=5)

        # --- Top Frame: Category Selector ---
        top_frame = tk.Frame(self, pady=10)
        top_frame.pack(fill="x")

        scrollable = ScrollableBox(self, box_count=20, on_click_callback=self.handle_box_click)
        scrollable.pack(fill="both", expand=True, padx=10, pady=10)

    def handle_box_click(self, index):
        print(f"You clicked box #{index + 1}")