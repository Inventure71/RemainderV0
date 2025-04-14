import tkinter as tk

class TopBar(tk.Frame):
    def __init__(self, root, controller):
        super().__init__(root, pady=10)
        self.pack(fill="x")

        tk.Button(self, text="Main Chat", command=lambda: controller.show_frame("MainChatWindow")).pack(side="left", padx=5)
        tk.Button(self, text="Projects", command=lambda: controller.show_frame("ProjectsWindow")).pack(side="left", padx=5)
        tk.Button(self, text="Project Chat", command=lambda: controller.show_frame("ProjectChatWindow")).pack(side="left", padx=5)
