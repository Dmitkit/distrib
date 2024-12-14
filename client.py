#client.py
import asyncio
import tkinter as tk
from tkinter import ttk
from logger_setup import get_logger
from tkinter import messagebox
import websockets
import json


logger = get_logger(__name__)

SCHEDULE_SERVER_IS_OUT = False
DISPATCHER_IP = 'localhost'
DISPATCHER_PORT = 30000
SCHEDULE_SERVER_IP = 'localhost'
SCHEDULE_SERVER_PORT = 20000
BACKUP_SCHEDULE_SERVER_IP = 'localhost'
BACKUP_SCHEDULE_SERVER_PORT = 20010


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
        self.backup_server_address = (BACKUP_SCHEDULE_SERVER_IP, BACKUP_SCHEDULE_SERVER_PORT)

        asyncio.create_task(self.initialize_server_address())

        self.schedule = []
        self.login = None
        self.websocket_task = None

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
        
        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
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
        
        scrollbar.config(command=self.range_listbox.yview)
        self.range_listbox.config(yscrollcommand=scrollbar.set)
        
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
        self.login = self.login_entry.get().strip()
        if self.login:
            self.save_login_button["state"] = "disabled"
            self.login_entry["state"] = "disabled"
            logger.info(f"Логин установлен: {self.login}")
        
    async def initialize_server_address(self):
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
        response = None
        global SCHEDULE_SERVER_IS_OUT

        if not SCHEDULE_SERVER_IS_OUT:
            response = await self.send_request("GET_SCHEDULE", self.schedule_server_address)
            if not response:
                SCHEDULE_SERVER_IS_OUT = True
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
            
            if (start_time, end_time) in user_reserved_slots:
                
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

        for index in selected_indices:
            if index < self.range_listbox.size():
                start_time, end_time = self.schedule[index][0:2]
                if (start_time, end_time) not in user_reserved_slots:
                    self.range_listbox.select_set(index)

    def reserve_ranges(self):
        if not self.login:
            messagebox.showwarning("Warning", "Please set your login first!")
            return

        selected_indices = self.range_listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("Info", "Please select time slots to reserve")
            return

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
    
    
    async def receive_notifications(self):
        """Принимает уведомления через WebSocket."""
        async with websockets.connect('ws://localhost:20005') as websocket:
            # Send identification message first
            await websocket.send(json.dumps({
                "type": "client_connected",
                "login": self.login
            }))
            
            logger.info("Клиент подключился к WebSocket-серверу.")
            try:
                while True:
                    message = await websocket.recv()
                    notification = json.loads(message)
                    
                    if notification["type"] == "notification":
                        if notification["status"] == "success" and notification.get("login") == self.login:
                            # Use your existing show_notification method
                            self.show_notification(
                                f"Ваша запись на {notification['start']}:00 - {notification['end']}:00 подтверждена!"
                            )
                        elif notification["status"] == "rejected":
                            # Show rejection message only if this client had requested this slot
                            start_time, end_time = notification['start'], notification['end']
                            if self.login in self.login_ranges:
                                range_str = str([(start_time, end_time)])
                                if range_str in self.login_ranges[self.login]:
                                    self.show_notification(
                                        f"Извините, но время {notification['start']}:00 - {notification['end']}:00 "
                                        "уже занято. \nПожалуйста, выберите другой слот."
                                    )
        
            except websockets.exceptions.ConnectionClosedError:
                logger.warning("Соединение с WebSocket-сервером закрыто.")
            except Exception as e:
                logger.exception(f"Ошибка получения уведомлений: {e}")
    
    async def handle_reservation(self, selected_ranges):
        ranges_message = f"CLIENT:{self.login}:{selected_ranges}"
        response = await self.send_request(ranges_message, self.primary_server_address)

        if response:
            if self.login not in self.login_ranges:
                self.login_ranges[self.login] = []
            self.login_ranges[self.login].append(str(selected_ranges))

            # Update UI
            self.update_schedule_ui()
            messagebox.showinfo("Success", "Time slots successfully reserved!")
            self.websocket_task = asyncio.create_task(self.receive_notifications()) # Запуск после успешного бронирования

        else:
            messagebox.showerror("Error", "Primary server is unavailable!")
            
    def show_notification(self, message):
        notification_window = tk.Toplevel(self.root)
        notification_window.title("Уведомление")
        notification_window.geometry("450x150")
        notification_label = ttk.Label(notification_window, text=message, font=('Arial', 12))
        notification_label.pack(pady=20, padx=20)
        notification_window.transient(self.root)
        notification_window.grab_set()

        notification_window.after(30000, notification_window.destroy)  # Закрытие через 3 секунды

    def on_closing(self):
        self.running = False
        if self.websocket_task:
            self.websocket_task.cancel()
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
