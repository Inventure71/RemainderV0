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

        # --- Existing navigation buttons ---
        tk.Button(self, text="Main Chat", command=lambda: controller.show_frame("MainChatWindow"), **btn_style).pack(side="left", padx=(8, 4), pady=6)
        tk.Button(self, text="Projects", command=lambda: controller.show_frame("ProjectsWindow"), **btn_style).pack(side="left", padx=4, pady=6)
        tk.Button(self, text="Project Chat", command=lambda: controller.show_frame("ProjectChatWindow"), **btn_style).pack(side="left", padx=(4, 8), pady=6)

        # --- Refresh Telegram Button ---
        refresh_btn = tk.Button(self, text="Refresh Telegram", command=self.refresh_telegram_messages, **btn_style)
        refresh_btn.pack(side="right", padx=(8, 16), pady=6)

    def refresh_telegram_messages(self):
        try:
            from Utils import telegram_utils
            telegram_utils.retrive_messages(save_to_file=True)
            # Optionally, add a callback to refresh the UI after fetching
            if hasattr(self.master, 'controller') and hasattr(self.master.controller, 'refresh_all_chats'):
                self.master.controller.refresh_all_chats()
        except Exception as e:
            import tkinter.messagebox as mb
            mb.showerror("Telegram Refresh Failed", f"Could not refresh messages from Telegram:\n{e}")
