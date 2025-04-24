import tkinter as tk

class TopBar(tk.Frame):
    def __init__(self, root, controller):
        super().__init__(root, pady=0, bg="#23272e")
        self.configure(highlightbackground="#2c2c2c", highlightthickness=1)

        btn_style = {
            "font": ("Arial", 12, "bold"),
            "bg": "#3a3f4b",
            "fg": "black",
            "activebackground": "#4e5a65",
            "activeforeground": "black",
            "bd": 0,
            "padx": 16,
            "pady": 8,
            "relief": "flat",
            "highlightthickness": 0,
        }

        tk.Button(self, text="Main Chat", command=lambda: controller.show_frame("MainChatWindow"), **btn_style).pack(side="left", padx=(8, 4), pady=6)
        tk.Button(self, text="Projects", command=lambda: controller.show_frame("ProjectsWindow"), **btn_style).pack(side="left", padx=4, pady=6)
        tk.Button(self, text="Project Chat", command=lambda: controller.show_frame("ProjectChatWindow"), **btn_style).pack(side="left", padx=(4, 8), pady=6)
