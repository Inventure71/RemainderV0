import tkinter as tk
from tkinter import messagebox

# --- Custom Scrollable Frame Class ---
class ScrollableFrame(tk.Frame):
    """A vertical scrollable frame that can hold other widgets."""
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

# --- App Setup ---
root = tk.Tk()
root.title("Simple To-Do App")
root.geometry("400x500")

# --- Top Frame: Category Selector ---
top_frame = tk.Frame(root, pady=10)
top_frame.pack(fill="x")

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

# --- Start the App ---
root.mainloop()
