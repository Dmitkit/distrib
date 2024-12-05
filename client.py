#client.py
import asyncio
import tkinter as tk
from tkinter import ttk
from logger_setup import get_logger
from tkinter import messagebox


logger = get_logger(__name__)

MAIN_SERVER_IS_OUT = False
DISPATCHER_IP = 'localhost'
DISPATCHER_PORT = 30000
BACKUP_SERVER_IP = 'localhost'
BACKUP_SERVER_PORT = 20004
SCHEDULE_SERVER_IP = 'localhost'
SCHEDULE_SERVER_PORT = 20000


class ScheduleClientApp:
    """Клиентское приложение для работы с расписанием."""

    def __init__(self, root):
        self.login_ranges = {}
        self.root = root
        self.root.title("Клиент расписания")
        self.root.geometry("600x700")
        
        self.root.configure(bg='#f0f5f9')
        
        style = ttk.Style()
        style.configure('Custom.TFrame', background='#f0f5f9')
        style.configure('Custom.TLabel', 
                   background='#f0f5f9',
                   font=('Arial', 12))
        style.configure('Custom.TButton',
                   font=('Arial', 11, 'bold'),
                   padding=10,
                   background='#1e88e5')

        self.primary_server_address = None
        self.schedule_server_address = (SCHEDULE_SERVER_IP, SCHEDULE_SERVER_PORT)
        self.backup_server_address = (BACKUP_SERVER_IP, BACKUP_SERVER_PORT)

        asyncio.create_task(self.initialize_server_address())

        self.schedule = []
        self.login = None

        # Ввод логина
        login_frame = ttk.Frame(root, style='Custom.TFrame')
        login_frame.pack(pady=20, padx=20, fill=tk.X)
        login_label = ttk.Label(login_frame, 
                           text="Введите ваш логин:",
                           style='Custom.TLabel')
        login_label.pack(side=tk.LEFT, padx=10)
        
        self.login_entry = tk.Entry(login_frame, 
                               font=('Arial', 12),
                               bg='white',
                               relief=tk.SOLID,
                               borderwidth=1)
        self.login_entry.pack(side=tk.LEFT, padx=10)

        self.save_login_button = tk.Button(
            login_frame,
            text="Save Login",
            command=self.set_login,
            font=('Arial', 11, 'bold'),
            bg='#1e88e5',
            fg='white',
            relief=tk.RAISED,
            padx=15,
            pady=5,
            cursor='hand2'
        )
        self.save_login_button.pack(side=tk.LEFT, padx=10)

        # Интерфейс расписания
        self.schedule_frame = ttk.Frame(root, style='Custom.TFrame')
        self.schedule_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        schedule_label = ttk.Label(root, 
                              text="Available Time Slots:",
                              style='Custom.TLabel')
        schedule_label.pack(pady=(10,5))
        
        # Create a frame for the listbox with scrollbar
        listbox_frame = ttk.Frame(root, style='Custom.TFrame')
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Enhanced Listbox
        self.range_listbox = tk.Listbox(
            listbox_frame,
            selectmode=tk.MULTIPLE,
            height=15,
            font=('Arial', 11),
            bg='white',
            selectbackground='#90caf9',
            selectforeground='black',
            relief=tk.SOLID,
            borderwidth=1
        )
        self.range_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Connect scrollbar to listbox
        scrollbar.config(command=self.range_listbox.yview)
        self.range_listbox.config(yscrollcommand=scrollbar.set)
        
        # Enhanced Reserve Button
        self.reserve_button = tk.Button(
            root,
            text="Reserve Selected Slots",
            command=self.reserve_ranges,
            font=('Arial', 12, 'bold'),
            bg='#2e7d32',  # Dark green
            fg='white',
            relief=tk.RAISED,
            padx=20,
            pady=10,
            cursor='hand2'
        )
        self.reserve_button.pack(pady=20)
        
        # Button hover effects
        def on_enter(e):
            e.widget['background'] = '#1565c0' if e.widget == self.save_login_button else '#1b5e20'
            
        def on_leave(e):
            e.widget['background'] = '#1e88e5' if e.widget == self.save_login_button else '#2e7d32'
        
        self.save_login_button.bind("<Enter>", on_enter)
        self.save_login_button.bind("<Leave>", on_leave)
        self.reserve_button.bind("<Enter>", on_enter)
        self.reserve_button.bind("<Leave>", on_leave)

        self.running = True
        self.root.after(2000, lambda: asyncio.create_task(self.update_schedule()))
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def set_login(self):
        """Сохраняет логин клиента."""
        self.login = self.login_entry.get().strip()
        if self.login:
            self.save_login_button["state"] = "disabled"
            self.login_entry["state"] = "disabled"
            logger.info(f"Логин установлен: {self.login}")

        
    async def initialize_server_address(self):
        """Получает адрес сервера от диспетчера и сохраняет его."""
        try:
            reader, writer = await asyncio.open_connection(DISPATCHER_IP, DISPATCHER_PORT)
            data = await reader.read(512)
            writer.close()
            await writer.wait_closed()

            self.primary_server_address = tuple(data.decode().split(":"))
            logger.info(f"Получен адрес сервера: {self.primary_server_address}")
        except Exception as e:
            logger.error(f"Ошибка при получении адреса сервера: {e}")

    async def send_request(self, message, server_address):
        """Отправляет запрос на сервер."""
        try:
            reader, writer = await asyncio.open_connection(*server_address)
            writer.write(message.encode())
            await writer.drain()
            data = await reader.read(512)
            writer.close()
            await writer.wait_closed()
            return data.decode()
        except Exception as e:
            logger.error(f"Ошибка отправки запроса: {e}")
            return None

    async def update_schedule(self):
        """Запрашивает расписание у сервера и обновляет интерфейс."""
        response = None
        global MAIN_SERVER_IS_OUT

        if not MAIN_SERVER_IS_OUT:
            response = await self.send_request("GET_SCHEDULE", self.schedule_server_address)
            if not response:
                MAIN_SERVER_IS_OUT = True
                logger.warning("Основной сервер недоступен. Переключаемся на резервный сервер.")
                response = await self.send_request("GET_SCHEDULE", self.backup_server_address)
        else:
            response = await self.send_request("GET_SCHEDULE", self.backup_server_address)

        if response:
            self.schedule = eval(response)
            self.update_schedule_ui()

        if self.running:
            self.root.after(2000, lambda: asyncio.create_task(self.update_schedule()))

    def update_schedule_ui(self):
        """Updates the schedule UI with enhanced styling and disables reserved slots."""
        selected_indices = list(self.range_listbox.curselection())
        self.range_listbox.delete(0, tk.END)
        
        # Store which slots are reserved by the current user
        user_reserved_slots = set()
        if self.login in self.login_ranges:
            # Convert string representation of ranges to actual tuples
            for range_str in self.login_ranges[self.login]:
                ranges = eval(range_str)
                for start, end in ranges:
                    user_reserved_slots.add((start, end))

        for i, (start_time, end_time, counter, color) in enumerate(self.schedule):
            display_text = f" {start_time:02d}:00 - {end_time:02d}:00  (Reserved: {counter})"
            self.range_listbox.insert(tk.END, display_text)
            
            # Enhanced colors with better visibility
            bg_colors = {
                'green': '#e8f5e9',    # Light green
                'orange': '#fff3e0',   # Light orange
                'red': '#ffebee'       # Light red
            }
            fg_colors = {
                'green': '#2e7d32',    # Dark green
                'orange': '#ef6c00',   # Dark orange
                'red': '#c62828'       # Dark red
            }
            
            # Check if this slot is reserved by the current user
            if (start_time, end_time) in user_reserved_slots:
                # Gray out reserved slots
                self.range_listbox.itemconfig(
                    tk.END,
                    {'bg': '#e0e0e0',  # Light gray background
                    'fg': '#9e9e9e'}  # Dark gray text
                )
                # Make the slot non-selectable
                self.range_listbox.itemconfig(tk.END, {'selectbackground': '#e0e0e0'})
                self.range_listbox.itemconfig(tk.END, {'selectforeground': '#9e9e9e'})
            else:
                self.range_listbox.itemconfig(
                    tk.END,
                    {'bg': bg_colors.get(color, '#ffffff'),
                    'fg': fg_colors.get(color, '#000000')}
                )

        # Restore selections for non-reserved slots
        for index in selected_indices:
            if index < self.range_listbox.size():
                start_time, end_time = self.schedule[index][0:2]
                if (start_time, end_time) not in user_reserved_slots:
                    self.range_listbox.select_set(index)

    def reserve_ranges(self):
        """Reserves selected time slots and disables them."""
        if not self.login:
            messagebox.showwarning("Warning", "Please set your login first!")
            return

        selected_indices = self.range_listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("Info", "Please select time slots to reserve")
            return

        # Check if any selected slots are already reserved
        selected_ranges = [self.schedule[i][0:2] for i in selected_indices]
        for start, end in selected_ranges:
            if self.login in self.login_ranges and str([(start, end)]) in self.login_ranges[self.login]:
                messagebox.showwarning("Warning", 
                    f"Time slot {start}:00-{end}:00 is already reserved by you")
                return

        if selected_ranges:
            asyncio.create_task(self.handle_reservation(selected_ranges))
            # Clear selections after reservation
            self.range_listbox.selection_clear(0, tk.END)

    def handle_click(self, event):
        """Handle click events on the listbox"""
        index = self.range_listbox.nearest(event.y)
        if index >= 0:
            start_time, end_time = self.schedule[index][0:2]
            if self.login in self.login_ranges:
                # Check if slot is already reserved by user
                for range_str in self.login_ranges[self.login]:
                    ranges = eval(range_str)
                    if (start_time, end_time) in ranges:
                        return "break"  # Prevent selection
        return None


    async def handle_reservation(self, selected_ranges):
        """Обрабатывает резервирование выбранных диапазонов."""
        ranges_message = f"CLIENT:{self.login}:{selected_ranges}"
        response = None
        global MAIN_SERVER_IS_OUT

        if not MAIN_SERVER_IS_OUT:
            response = await self.send_request(ranges_message, self.primary_server_address)
            if not response:
                MAIN_SERVER_IS_OUT = True
                logger.warning("Основной сервер недоступен. Переключаемся на резервный сервер.")
                response = await self.send_request(ranges_message, self.backup_server_address)
        else:
            response = await self.send_request(ranges_message, self.backup_server_address)

        if response:
            if self.login not in self.login_ranges:
                self.login_ranges[self.login] = []
            self.login_ranges[self.login].append(str(selected_ranges))
            
            # Update UI
            self.update_schedule_ui()
            messagebox.showinfo("Success", "Time slots successfully reserved!")

    def on_closing(self):
        """Метод для обработки закрытия окна."""
        self.running = False
        self.root.quit()


async def main():
    root = tk.Tk()
    app = ScheduleClientApp(root)
    
    try:
        while app.running:
            app.root.update()
            await asyncio.sleep(0.01)
    except tk.TclError:
        logger.info("Окно закрыто, приложение завершено.")


if __name__ == "__main__":
    asyncio.run(main())
