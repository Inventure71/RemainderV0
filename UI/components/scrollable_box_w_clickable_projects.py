import tkinter as tk

class ScrollableBox(tk.Frame):
    def __init__(self, parent, box_count=20, project_dictionary=None, columns=4, on_click_callback=None):
        super().__init__(parent)

        self.columns = columns
        self.on_click_callback = on_click_callback

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

        self.update_projects(project_dictionary, box_count, on_click_callback)


    def on_click(self, idx, callback):
        if callback:
            callback(idx)
        else:
            print(f"Box {idx+1} clicked!")

    def update_projects(self, projects_dictionary=None, box_count=20, on_click_callback=None):
        # clear existing boxes
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if on_click_callback:
            self.on_click_callback = on_click_callback

        if projects_dictionary:
            for i, project in enumerate(projects_dictionary):
                row = i // self.columns
                col = i % self.columns

                # Determine box color and outline
                box_color = project.get("color", "#dddddd")
                # Use a special outline color for non-user-created projects
                if not project.get("user_created", 0):
                    highlight_color = "#FF5733"  # Example: bright orange outline
                else:
                    highlight_color = "#228B22"  # Example: green outline

                box = tk.Frame(self.scrollable_frame, borderwidth=3, relief="raised",
                               bg=box_color, highlightbackground=highlight_color, highlightcolor=highlight_color, highlightthickness=3, padx=10, pady=10)
                box.grid(row=row, column=col, padx=10, pady=5, sticky="nw")

                label = tk.Label(box, text=project["name"][:3].upper(), bg=box_color)
                label.pack()

                box.bind("<Button-1>", lambda e, idx=i: self.on_click(idx, self.on_click_callback))
                label.bind("<Button-1>", lambda e, idx=i: self.on_click(idx, self.on_click_callback))

        else:
            for i in range(box_count):
                row = i // self.columns
                col = i % self.columns

                box = tk.Frame(self.scrollable_frame, borderwidth=2, relief="raised",
                               bg="#dddddd", padx=10, pady=10)
                box.grid(row=row, column=col, padx=10, pady=5, sticky="nw")

                label = tk.Label(box, text=f"Item {i + 1}", bg="#dddddd")
                label.pack()

                box.bind("<Button-1>", lambda e, idx=i: self.on_click(idx, self.on_click_callback))
                label.bind("<Button-1>", lambda e, idx=i: self.on_click(idx, self.on_click_callback))



# --- Main App Window ---
def main():
    root = tk.Tk()
    root.title("Scrollable Clickable Boxes")
    root.geometry("400x500")

    def handle_click(index):
        print(f"You clicked box #{index + 1}")

    scrollable = ScrollableBox(root, box_count=20)#on_click_callback=handle_click)
    scrollable.pack(fill="both", expand=True, padx=10, pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()
