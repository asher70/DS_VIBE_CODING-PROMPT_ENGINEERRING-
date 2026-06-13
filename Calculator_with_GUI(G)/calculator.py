import tkinter as tk


def main():
    root = tk.Tk()
    root.title("Calculator")
    root.geometry("400x600")
    root.resizable(False, False)
    root.configure(bg="#1c1c1c")

    display = tk.Entry(
        root, font=("Segoe UI", 40), justify="right",
        bg="#1c1c1c", fg="#ffffff", insertbackground="#ffffff",
        relief="flat", highlightthickness=1, highlightcolor="#333333",
    )
    display.grid(row=0, column=0, sticky="nsew", padx=15, pady=(20, 10))

    button_frame = tk.Frame(root, bg="#1c1c1c")
    button_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    for i in range(4):
        button_frame.grid_columnconfigure(i, weight=1, uniform="col")
    for i in range(5):
        button_frame.grid_rowconfigure(i, weight=1, uniform="row")

    first_number = None
    current_operator = None

    def on_click(digit):
        current = display.get()
        if current == "Error":
            current = ""
        display.delete(0, tk.END)
        display.insert(0, current + digit)

    def on_operator(operator):
        nonlocal first_number, current_operator
        value = display.get()
        if value == "" or value == "Error":
            display.delete(0, tk.END)
            display.insert(0, "Error")
            first_number = None
            current_operator = None
            return
        first_number = value
        current_operator = operator
        display.delete(0, tk.END)

    def on_equals():
        nonlocal first_number, current_operator
        second_number = display.get()
        if first_number is None or current_operator is None:
            return
        if first_number == "" or second_number == "" or second_number == "Error":
            display.delete(0, tk.END)
            display.insert(0, "Error")
            first_number = None
            current_operator = None
            return
        try:
            a = float(first_number)
            b = float(second_number)
        except ValueError:
            display.delete(0, tk.END)
            display.insert(0, "Error")
            first_number = None
            current_operator = None
            return
        if current_operator == '+':
            result = a + b
        elif current_operator == '-':
            result = a - b
        elif current_operator == '*':
            result = a * b
        elif current_operator == '/':
            if b == 0:
                display.delete(0, tk.END)
                display.insert(0, "Error")
                first_number = None
                current_operator = None
                return
            result = a / b
        else:
            return
        if result == int(result):
            result = int(result)
        display.delete(0, tk.END)
        display.insert(0, str(result))
        first_number = None
        current_operator = None

    def on_clear():
        nonlocal first_number, current_operator
        display.delete(0, tk.END)
        first_number = None
        current_operator = None

    buttons = [
        ('7', 1, 0), ('8', 1, 1), ('9', 1, 2),
        ('4', 2, 0), ('5', 2, 1), ('6', 2, 2),
        ('1', 3, 0), ('2', 3, 1), ('3', 3, 2),
        ('0', 4, 0),
    ]

    number_style = {"font": ("Segoe UI", 22, "bold"), "bg": "#333333", "fg": "#ffffff",
                    "activebackground": "#444444", "activeforeground": "#ffffff",
                    "relief": "flat", "borderwidth": 0}
    operator_style = {"font": ("Segoe UI", 22, "bold"), "bg": "#ff9500", "fg": "#ffffff",
                      "activebackground": "#ffb143", "activeforeground": "#ffffff",
                      "relief": "flat", "borderwidth": 0}
    equals_style = {"font": ("Segoe UI", 22, "bold"), "bg": "#2c9bdb", "fg": "#ffffff",
                    "activebackground": "#5cb3e8", "activeforeground": "#ffffff",
                    "relief": "flat", "borderwidth": 0}
    clear_style = {"font": ("Segoe UI", 22, "bold"), "bg": "#a5a5a5", "fg": "#000000",
                   "activebackground": "#bdbdbd", "activeforeground": "#000000",
                   "relief": "flat", "borderwidth": 0}

    for text, row, col in buttons:
        colspan = 2 if text == '0' else 1
        btn = tk.Button(button_frame, text=text, **number_style, command=lambda t=text: on_click(t))
        btn.grid(row=row, column=col, columnspan=colspan, sticky="nsew", padx=1, pady=1)

    operators = [
        ('+', 1, 3), ('-', 2, 3), ('*', 3, 3), ('/', 4, 3),
    ]

    for text, row, col in operators:
        btn = tk.Button(button_frame, text=text, **operator_style, command=lambda t=text: on_operator(t))
        btn.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)

    eq_btn = tk.Button(button_frame, text='=', **equals_style, command=on_equals)
    eq_btn.grid(row=4, column=2, sticky="nsew", padx=1, pady=1)

    clear_btn = tk.Button(button_frame, text='C', **clear_style, command=on_clear)
    clear_btn.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=1, pady=1)

    root.grid_rowconfigure(1, weight=1)
    root.grid_columnconfigure(0, weight=1)
    root.mainloop()


if __name__ == "__main__":
    main()
