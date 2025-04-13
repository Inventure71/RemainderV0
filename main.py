import tkinter as tk
from tkinter import messagebox
from UI.window_projects import ProjectsWindow
from UI.window_main_chat import MainChatWindow

# --- App Setup ---
class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Remainder")
        self.geometry("1080x720")

        # Create a container frame to stack pages
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Dictionary to store pages by name
        self.frames = {}

        for F in (MainChatWindow, ProjectsWindow):
            page_name = F.__name__  # e.g., "MainChatWindow"
            frame = F(parent=container, controller=self)
            frame.grid(row=0, column=0, sticky="nsew")
            self.frames[page_name] = frame

        self.show_frame("MainChatWindow")

    def show_frame(self, page_name: str):
        """Raise the frame to the top by string name"""
        frame = self.frames[page_name]
        frame.tkraise()



"""

tk.Label(self, text="Main Menu", font=("Arial", 16)).pack(pady=10)
        tk.Button(self, text="Go to Second Menu",
                  command=lambda: controller.show_frame(SecondMenu)).pack()


"""
"""
tk.Label(top_frame, text="Select Category:").pack(side="left", padx=5)

categories = ["Work", "Personal", "Study"]
selected_category = tk.StringVar(value=categories[0])
category_menu = tk.OptionMenu(top_frame, selected_category, *categories)
category_menu.pack(side="left")

# --- Middle Frame: Task Entry ---
entry_frame = tk.Frame(root, pady=10)
entry_frame.pack(fill="x")

tk.Label(entry_frame, text="Task:").pack(side="left", padx=5)
task_entry = tk.Entry(entry_frame)
task_entry.pack(side="left", fill="x", expand=True, padx=5)

# Button to add task
def add_task():
    task = task_entry.get()
    category = selected_category.get()
    if task:
        listbox.insert(tk.END, f"[{category}] {task}")
        task_entry.delete(0, tk.END)
    else:
        messagebox.showwarning("Empty Task", "Please enter a task first.")

tk.Button(entry_frame, text="Add Task", command=add_task).pack(side="right", padx=5)

# --- Center Frame: Scrollable Task List ---
task_list_frame = tk.LabelFrame(root, text="Tasks", padx=5, pady=5)
task_list_frame.pack(fill="both", expand=True, padx=10, pady=10)

scrollable = ScrollableFrame(task_list_frame)
scrollable.pack(fill="both", expand=True)

# Add a listbox inside the scrollable frame
listbox = tk.Listbox(scrollable.scrollable_frame)
listbox.pack(fill="both", expand=True)

# --- Bottom Frame: Action Buttons ---
bottom_frame = tk.Frame(root, pady=10)
bottom_frame.pack(fill="x")

def delete_task():
    selected = listbox.curselection()
    if selected:
        listbox.delete(selected[0])
    else:
        messagebox.showinfo("No selection", "Select a task to delete.")

tk.Button(bottom_frame, text="Delete Selected", command=delete_task).pack(pady=5)

# --- Custom Scrollable Frame Class ---
class ScrollableFrame(tk.Frame):
    
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)

        canvas = tk.Canvas(self)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
"""
# --- Start the App ---
if __name__ == "__main__":
    app = App()
    app.mainloop()
