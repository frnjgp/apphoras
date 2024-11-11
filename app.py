import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
import sqlite3

def initialize_database():
    conn = sqlite3.connect('work_hours.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS work_hours (
                        week_key TEXT,
                        day INTEGER,
                        entry TEXT,
                        exit TEXT,
                        worked TEXT,
                        total TEXT,
                        owe_time TEXT,
                        accumulated_overtime TEXT,
                        reset_flag INTEGER DEFAULT 0,
                        PRIMARY KEY (week_key, day)
                    )''')
    conn.commit()
    conn.close()

def save_week_data(week_key, data):
    conn = sqlite3.connect('work_hours.db')
    cursor = conn.cursor()
    # Save daily data
    for day, values in data.items():
        if isinstance(values, dict) and day != 'reset_flag':
            cursor.execute('''INSERT OR REPLACE INTO work_hours 
                              (week_key, day, entry, exit, worked)
                              VALUES (?, ?, ?, ?, ?)''',
                           (week_key, day, values.get('entry', ''), values.get('exit', ''), values.get('worked', '0:00')))
    # Save the weekly totals with day = -1
    cursor.execute('''INSERT OR REPLACE INTO work_hours
                      (week_key, day, total, owe_time, accumulated_overtime, reset_flag)
                      VALUES (?, ?, ?, ?, ?, ?)''',
                   (week_key, -1, data.get('total', '0:00'), data.get('owe_time', '0:00'), data.get('accumulated_overtime', '0:00'), data.get('reset_flag', 0)))
    conn.commit()
    conn.close()

def load_week_data_from_db(week_key):
    conn = sqlite3.connect('work_hours.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT day, entry, exit, worked, total, owe_time, accumulated_overtime, reset_flag 
                      FROM work_hours WHERE week_key = ?''', (week_key,))
    rows = cursor.fetchall()
    conn.close()

    data = {}
    if rows:
        for row in rows:
            day = row[0]
            if day == -1:
                # This is the weekly totals row
                total_hours.set(row[4] if row[4] else "0:00")
                owe_hours.set(row[5] if row[5] else "0:00")
                total_overtime.set(row[6] if row[6] else "0:00")
                data['total'] = row[4] if row[4] else "0:00"
                data['owe_time'] = row[5] if row[5] else "0:00"
                data['accumulated_overtime'] = row[6] if row[6] else "0:00"
                data['reset_flag'] = row[7]
            else:
                data[day] = {"entry": row[1], "exit": row[2], "worked": row[3]}
    else:
        # If no data for this week, reset totals but load accumulated overtime from previous week
        total_hours.set("0:00")
        owe_hours.set("0:00")
        accumulated_overtime = calculate_accumulated_overtime(week_key)
        total_overtime.set(format_timedelta(accumulated_overtime))
        data['accumulated_overtime'] = format_timedelta(accumulated_overtime)
        data['reset_flag'] = 0

    return data

def clear_database():
    if messagebox.askyesno("Confirmar", "¿Estás seguro de que deseas limpiar todos los datos de la base de datos?"):
        conn = sqlite3.connect('work_hours.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM work_hours")
        conn.commit()
        conn.close()

        # Clear the UI data
        for i in range(5):
            entry_time_vars[i].set("")
            exit_time_vars[i].set("")
            daily_hours_vars[i].set("0:00")
        total_hours.set("0:00")
        max_hours_weekly.set("0:00")
        owe_hours.set("0:00")
        total_overtime.set("0:00")
        weekly_data.clear()

        messagebox.showinfo("Base de datos limpia", "Todos los datos han sido eliminados correctamente.")

# Initialize the database
initialize_database()

# Application setup
root = tk.Tk()
root.title("Registro de Horas de Trabajo")

# Variables
entry_time_vars = []
exit_time_vars = []
daily_hours_vars = []
date_labels = []
total_hours = tk.StringVar(value="0:00")
max_hours_weekly = tk.StringVar(value="0:00")
owe_hours = tk.StringVar(value="0:00")
total_overtime = tk.StringVar(value="0:00")  # Acumulado de horas extra

# Modify the week_key to use the Monday date as key
current_week_start = datetime.now() - timedelta(days=datetime.now().weekday())
week_display = tk.StringVar(value=f"Semana del {current_week_start.strftime('%d/%m/%Y')}")

# Data stored for each week
weekly_data = {}

# Function to update the displayed week
def update_week_display():
    week_display.set(f"Semana del {current_week_start.strftime('%d/%m/%Y')}")
    load_week_data()

    # Update the day labels with corresponding dates
    for i in range(5):
        day_date = current_week_start + timedelta(days=i)
        date_labels[i].config(text=f"{days[i]} {day_date.strftime('%d/%m')}")

# Function to load week data
def load_week_data():
    week_key = current_week_start.strftime("%Y-%m-%d")  # Use the date of the Monday as the week key
    data = load_week_data_from_db(week_key)

    # Initialize weekly_data for the current week
    weekly_data[week_key] = data

    for i in range(5):
        entry_time_vars[i].set(data.get(i, {}).get("entry", ""))
        exit_time_vars[i].set(data.get(i, {}).get("exit", ""))
        daily_hours_vars[i].set(data.get(i, {}).get("worked", "0:00"))

    # Calculate maximum weekly hours based on worked days
    max_hours = timedelta(hours=8) * sum(1 for i in range(5) if data.get(i, {}).get("entry") and data.get(i, {}).get("exit"))
    max_hours_weekly.set(format_timedelta(max_hours))

    # Ensure the accumulated overtime from previous week is displayed
    accumulated_overtime = calculate_accumulated_overtime(week_key)
    total_overtime.set(format_timedelta(accumulated_overtime))
    weekly_data[week_key]['accumulated_overtime'] = format_timedelta(accumulated_overtime)

    # Update owe_hours if not loaded
    owe_hours.set(data.get('owe_time', "0:00"))
    total_hours.set(data.get('total', "0:00"))

def validate_time_format(var, day_index, is_entry):
    time_text = var.get()
    if time_text.isdigit() and len(time_text) <= 2:
        var.set(f"{time_text}:00")

    # Ensure the day is initialized in weekly_data
    week_key = current_week_start.strftime("%Y-%m-%d")
    if week_key not in weekly_data:
        weekly_data[week_key] = {}
    if day_index not in weekly_data[week_key]:
        weekly_data[week_key][day_index] = {"entry": "", "exit": "", "worked": "0:00"}

    if is_entry:
        weekly_data[week_key][day_index]["entry"] = var.get()
    else:
        weekly_data[week_key][day_index]["exit"] = var.get()

def calculate_hours(event=None):
    total = timedelta()
    worked_days = 0
    week_key = current_week_start.strftime("%Y-%m-%d")
    weekly_data[week_key] = weekly_data.get(week_key, {})

    for i in range(5):
        entry_text = entry_time_vars[i].get()
        exit_text = exit_time_vars[i].get()

        if entry_text and exit_text:
            try:
                entry_time = datetime.strptime(entry_text, "%H:%M")
                exit_time = datetime.strptime(exit_text, "%H:%M")
                worked_time = exit_time - entry_time
                if worked_time.days < 0:
                    worked_time += timedelta(days=1)  # Adjust for overnight shifts
                daily_hours_vars[i].set(str(worked_time))
                total += worked_time
                worked_days += 1

                weekly_data[week_key][i] = {
                    "entry": entry_text,
                    "exit": exit_text,
                    "worked": str(worked_time),
                }
            except ValueError:
                messagebox.showwarning("Formato incorrecto", "Por favor ingresa las horas en formato HH:MM")
                return
        else:
            daily_hours_vars[i].set("0:00")

    total_hours.set(format_timedelta(total))
    weekly_data[week_key]["total"] = format_timedelta(total)

    max_hours = timedelta(hours=8) * worked_days
    owe_time = total - max_hours

    max_hours_weekly.set(format_timedelta(max_hours))
    weekly_data[week_key]["owe_time"] = format_timedelta(owe_time)
    owe_hours.set(format_timedelta(owe_time))

    # Get accumulated overtime from the previous week
    prev_accumulated_overtime = calculate_accumulated_overtime(week_key)

    # Check if reset_flag is set
    reset_flag = weekly_data[week_key].get('reset_flag', 0)
    if reset_flag == 1:
        prev_accumulated_overtime = timedelta()

    # Calculate current accumulated overtime
    current_accumulated_overtime = prev_accumulated_overtime + owe_time
    total_overtime.set(format_timedelta(current_accumulated_overtime))
    weekly_data[week_key]["accumulated_overtime"] = format_timedelta(current_accumulated_overtime)

    # Save data to the database
    save_week_data(week_key, weekly_data[week_key])

def calculate_accumulated_overtime(current_week_key):
    # Calculate the previous week's key
    current_week_start_date = datetime.strptime(current_week_key, "%Y-%m-%d")
    week_start_date = current_week_start_date - timedelta(weeks=1)

    accumulated_overtime = timedelta()

    while True:
        previous_week_key = week_start_date.strftime("%Y-%m-%d")

        conn = sqlite3.connect('work_hours.db')
        cursor = conn.cursor()
        cursor.execute('SELECT owe_time, accumulated_overtime, reset_flag FROM work_hours WHERE week_key = ? AND day = -1', (previous_week_key,))
        row = cursor.fetchone()
        conn.close()

        if row:
            reset_flag = row[2]
            if reset_flag == 1:
                # Reset occurred in this week
                accumulated_overtime = timedelta()
                break
            else:
                accumulated_overtime = parse_timedelta(row[1]) if row[1] else timedelta()
                break
        else:
            # No more previous records
            break

        week_start_date -= timedelta(weeks=1)

    return accumulated_overtime

def reset_accumulated_overtime():
    if messagebox.askyesno("Confirmar Reset", "¿Estás seguro de que deseas reiniciar el acumulado de horas extra a partir de esta semana?"):
        week_key = current_week_start.strftime("%Y-%m-%d")
        # Set the reset_flag for the current week
        weekly_data[week_key]['reset_flag'] = 1
        weekly_data[week_key]['accumulated_overtime'] = "0:00"
        total_overtime.set("0:00")
        # Save the changes to the database
        save_week_data(week_key, weekly_data[week_key])
        messagebox.showinfo("Reset Acumulado", "El acumulado de horas extra se ha reiniciado a partir de esta semana.")

        # Recalculate accumulated overtime for subsequent weeks
        # Optionally, you can implement logic to update following weeks

def format_timedelta(td):
    total_seconds = int(td.total_seconds())
    sign = "-" if total_seconds < 0 else ""
    total_seconds = abs(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{sign}{hours}:{minutes:02d}"

def parse_timedelta(time_str):
    sign = -1 if time_str.startswith('-') else 1
    time_str = time_str.lstrip('-')
    try:
        hours, minutes = map(int, time_str.split(':'))
        return timedelta(hours=hours, minutes=minutes) * sign
    except ValueError:
        return timedelta()

def previous_week():
    global current_week_start
    # Save current week's data before changing
    week_key = current_week_start.strftime("%Y-%m-%d")
    calculate_hours()  # Ensure hours are calculated and data is saved
    save_week_data(week_key, weekly_data.get(week_key, {}))

    # Move to the previous week and update UI
    current_week_start -= timedelta(weeks=1)
    update_week_display()

def next_week():
    global current_week_start
    # Save current week's data before changing
    week_key = current_week_start.strftime("%Y-%m-%d")
    calculate_hours()  # Ensure hours are calculated and data is saved
    save_week_data(week_key, weekly_data.get(week_key, {}))

    # Move to the next week and update UI
    current_week_start += timedelta(weeks=1)
    update_week_display()

# User Interface
tk.Label(root, text="Semana:").grid(row=0, column=0)
tk.Label(root, textvariable=week_display).grid(row=0, column=1, columnspan=2)
tk.Button(root, text="Semana Anterior", command=previous_week).grid(row=0, column=3)
tk.Button(root, text="Semana Siguiente", command=next_week).grid(row=0, column=4)

tk.Label(root, text="Día").grid(row=1, column=0)
tk.Label(root, text="Entrada (HH:MM)").grid(row=1, column=1)
tk.Label(root, text="Salida (HH:MM)").grid(row=1, column=2)
tk.Label(root, text="Horas Diarias").grid(row=1, column=3)

days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
for i, day in enumerate(days):
    day_date = current_week_start + timedelta(days=i)
    day_label = tk.Label(root, text=f"{day} {day_date.strftime('%d/%m')}")
    day_label.grid(row=i+2, column=0)
    date_labels.append(day_label)

    entry_time_var = tk.StringVar()
    exit_time_var = tk.StringVar()
    daily_hours_var = tk.StringVar(value="0:00")

    entry_time_vars.append(entry_time_var)
    exit_time_vars.append(exit_time_var)
    daily_hours_vars.append(daily_hours_var)

    entry = tk.Entry(root, textvariable=entry_time_var)
    exit_entry = tk.Entry(root, textvariable=exit_time_var)

    entry.grid(row=i+2, column=1)
    exit_entry.grid(row=i+2, column=2)

    # Bind validation and calculation
    entry.bind("<FocusOut>", lambda e, var=entry_time_var, day=i: validate_time_format(var, day, True))
    entry.bind("<Return>", lambda e, var=entry_time_var, day=i: validate_time_format(var, day, True))

    exit_entry.bind("<FocusOut>", lambda e, var=exit_time_var, day=i: validate_time_format(var, day, False))
    exit_entry.bind("<Return>", lambda e, var=exit_time_var, day=i: validate_time_format(var, day, False))

    # Bind Enter key to calculate hours
    entry.bind("<Return>", calculate_hours)
    exit_entry.bind("<Return>", calculate_hours)

    tk.Label(root, textvariable=daily_hours_var).grid(row=i+2, column=3)

tk.Button(root, text="Calcular Horas", command=calculate_hours).grid(row=8, column=1, columnspan=2)
tk.Label(root, text="Total Semanal:").grid(row=9, column=0)
tk.Label(root, textvariable=total_hours).grid(row=9, column=1, columnspan=2)

tk.Label(root, text="Horas Máximas Semanales:").grid(row=10, column=0)
tk.Label(root, textvariable=max_hours_weekly).grid(row=10, column=1, columnspan=2)

tk.Label(root, text="Horas Extra Semana Actual:").grid(row=11, column=0)
tk.Label(root, textvariable=owe_hours).grid(row=11, column=1, columnspan=2)

tk.Label(root, text="Horas Extra Acumuladas:").grid(row=12, column=0)
tk.Label(root, textvariable=total_overtime).grid(row=12, column=1, columnspan=2)

clear_db_button = tk.Button(root, text="Limpiar Base de Datos", command=clear_database)
clear_db_button.grid(row=13, column=1, columnspan=2)

reset_button = tk.Button(root, text="Reset Acumulado", command=reset_accumulated_overtime)
reset_button.grid(row=14, column=1, columnspan=2)

# Load the current week on startup
update_week_display()
root.mainloop()
