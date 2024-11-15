import asyncio
import tkinter as tk
from tkinter import ttk


class ScheduleClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Клиент расписания")
        self.root.geometry("400x400")

        self.server_address = ('localhost', 12345)
        self.schedule = []
        self.login = None  # Логин клиента

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

        # Асинхронное обновление расписания
        self.root.after(2000, lambda: asyncio.create_task(self.update_schedule()))

    def set_login(self):
        """Сохраняет логин клиента."""
        self.login = self.login_entry.get().strip()
        if self.login:
            self.save_login_button["state"] = "disabled"
            self.login_entry["state"] = "disabled"
            print(f"Логин установлен: {self.login}")

    async def send_request(self, message):
        """Асинхронно отправляет запрос на сервер и получает ответ."""
        try:
            reader, writer = await asyncio.open_connection(*self.server_address)
            writer.write(message.encode())
            await writer.drain()

            data = await reader.read(1024)
            writer.close()
            await writer.wait_closed()

            return data.decode()
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            return None

    async def update_schedule(self):
        """Запрашивает расписание у сервера и обновляет интерфейс."""
        response = await self.send_request("GET_SCHEDULE")
        if response:
            self.schedule = eval(response)  # Преобразуем строку в список
            self.update_schedule_ui()

        # Планируем следующее обновление через 10 секунд
        self.root.after(2000, lambda: asyncio.create_task(self.update_schedule()))

    def update_schedule_ui(self):
        """Обновляет интерфейс с расписанием."""
        selected_indices = list(self.range_listbox.curselection())  # Сохраняем текущие выбранные индексы

        self.range_listbox.delete(0, tk.END)

        for start_time, end_time, counter, color in self.schedule:
            display_text = f"{start_time:02d}-{end_time:02d} (Занято: {counter})"
            self.range_listbox.insert(tk.END, display_text)
            self.range_listbox.itemconfig(tk.END, {'bg': color})

        # Восстанавливаем выбор
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
        response = await self.send_request(ranges_message)
        if response:
            self.schedule = eval(response)  # Преобразуем строку в список
            self.update_schedule_ui()

async def main():
    root = tk.Tk()
    app = ScheduleClientApp(root)

    # Запускаем tkinter в asyncio-петле
    while True:
        app.root.update()
        await asyncio.sleep(0.01)


if __name__ == "__main__":
    asyncio.run(main())
