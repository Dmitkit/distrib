#client.py
import asyncio
import tkinter as tk
from tkinter import ttk

# Global server configuration
MAIN_SERVER_IS_OUT = False
DISPATCHER_IP = 'localhost'
DISPATCHER_PORT = 30000
BACKUP_SERVER_IP = 'localhost'
BACKUP_SERVER_PORT = 20002


class ScheduleClientApp:
    def __init__(self, root):

        self.root = root
        self.root.title("Клиент расписания")
        self.root.geometry("400x400")

        self.primary_server_address = None
        self.backup_server_address = (BACKUP_SERVER_IP, BACKUP_SERVER_PORT)

        asyncio.create_task(self.initialize_server_address())

        self.schedule = []
        self.login = None

        # Ввод логина
        login_frame = ttk.Frame(root)
        login_frame.pack(pady=5)
        ttk.Label(login_frame, text="Введите ваш логин:").pack(side=tk.LEFT, padx=5)
        self.login_entry = ttk.Entry(login_frame)
        self.login_entry.pack(side=tk.LEFT)

        self.save_login_button = ttk.Button(
            login_frame, text="Сохранить логин", command=self.set_login)
        self.save_login_button.pack(side=tk.LEFT, padx=5)

        # Интерфейс расписания
        self.schedule_frame = ttk.Frame(root)
        self.schedule_frame.pack(fill=tk.BOTH, expand=True)

        self.range_listbox = tk.Listbox(
            root, selectmode=tk.MULTIPLE, height=10)
        self.range_listbox.pack(pady=5)

        self.reserve_button = ttk.Button(
            root, text="Зарезервировать выбранные", command=self.reserve_ranges)
        self.reserve_button.pack(pady=5)

        self.running = True

        self.root.after(2000, lambda: asyncio.create_task(self.update_schedule()))

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def set_login(self):
        """Сохраняет логин клиента."""
        self.login = self.login_entry.get().strip()
        if self.login:
            self.save_login_button["state"] = "disabled"
            self.login_entry["state"] = "disabled"
            print(f"Логин установлен: {self.login}")

        
    async def initialize_server_address(self):
        """Получает адрес сервера от диспетчера и сохраняет его."""
        reader, writer = await asyncio.open_connection(DISPATCHER_IP, DISPATCHER_PORT)  # Подключение к диспетчеру
        data = await reader.read(512)
        writer.close()
        await writer.wait_closed()

        # Сохраняем адрес сервера
        self.primary_server_address = tuple(data.decode().split(":"))
        print(f"Получен адрес сервера: {self.primary_server_address}")


    async def send_request(self, message, server_address):
        try:
            reader, writer = await asyncio.open_connection(*server_address)
            writer.write(message.encode())
            await writer.drain()
            data = await reader.read(512)
            writer.close()
            await writer.wait_closed()
            return data.decode()
        except Exception:
            return None
        

    async def update_schedule(self):
        """Запрашивает расписание у сервера и обновляет интерфейс."""
        response = None

        # Если основной сервер недоступен, переключаемся на резервный сервер
        global MAIN_SERVER_IS_OUT

        if not MAIN_SERVER_IS_OUT:
            response = await self.send_request("GET_SCHEDULE", self.primary_server_address)
            if not response:
                MAIN_SERVER_IS_OUT = True
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

        for start_time, end_time, counter, color in self.schedule:
            display_text = f"{start_time:02d}-{end_time:02d} (Занято: {counter})"
            self.range_listbox.insert(tk.END, display_text)
            self.range_listbox.itemconfig(tk.END, {'bg': color})

        for index in selected_indices:
            self.range_listbox.select_set(index)

    
    def reserve_ranges(self):
        """Резервирует выбранные диапазоны."""
        if not self.login:
            print("Логин не установлен!")
            return

        selected_indices = self.range_listbox.curselection()
        selected_ranges = [self.schedule[i][0:2] for i in selected_indices]
        if selected_ranges:
            asyncio.create_task(self.handle_reservation(selected_ranges))


    async def handle_reservation(self, selected_ranges):
        """Обрабатывает резервирование выбранных диапазонов."""
        ranges_message = f"{self.login}:{selected_ranges}"
        response = None
        global MAIN_SERVER_IS_OUT

        if not MAIN_SERVER_IS_OUT:
            response = await self.send_request(ranges_message, self.primary_server_address)
            if not response:
                MAIN_SERVER_IS_OUT = True
                print("Основной сервер недоступен, пытаемся подключиться к резервному серверу.")
        else:
            response = await self.send_request(ranges_message, self.backup_server_address)

        if response:
            self.schedule = eval(response)
            self.update_schedule_ui()

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
        print("Окно закрыто, приложение завершено.")


if __name__ == "__main__":
    asyncio.run(main())
