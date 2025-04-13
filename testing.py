import tkinter as tk

def select_item(value):
    print(f"Selected: {value}")

root = tk.Tk()
root.title("Nested Selection Menu")
root.geometry("300x200")

# Button to trigger the menu
btn = tk.Menubutton(root, text="Select Category", relief="raised")
btn.grid(padx=20, pady=20)

# Create main menu
main_menu = tk.Menu(btn, tearoff=False)
btn.config(menu=main_menu)

# --- Submenu: Food ---
food_menu = tk.Menu(main_menu, tearoff=False)
food_menu.add_command(label="Pizza", command=lambda: select_item("Pizza"))
food_menu.add_command(label="Sushi", command=lambda: select_item("Sushi"))

# --- Submenu: Drinks ---
drinks_menu = tk.Menu(main_menu, tearoff=False)
drinks_menu.add_command(label="Coffee", command=lambda: select_item("Coffee"))
drinks_menu.add_command(label="Juice", command=lambda: select_item("Juice"))

# Add submenus to main menu
main_menu.add_cascade(label="Food", menu=food_menu)
main_menu.add_cascade(label="Drinks", menu=drinks_menu)

root.mainloop()
