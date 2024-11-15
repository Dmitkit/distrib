import asyncio
import json
import os

# Список расписания
schedule = [
    (9, 10, 0, 'green'),
    (10, 11, 0, 'green'),
    (11, 12, 0, 'green'),
    (12, 13, 0, 'green'),
    (13, 14, 0, 'green'),
    (14, 15, 0, 'green'),
    (15, 16, 0, 'green'),
    (16, 17, 0, 'green'),
    (17, 18, 0, 'green'),
    (18, 19, 0, 'green'),
    (19, 20, 0, 'green')
]

backup_file = "schedule_backup.json"
clients_data = {}
schedule_lock = asyncio.Lock()


def save_backup():
    """Сохраняет расписание в файл бэкапа."""
    with open(backup_file, "w") as f:
        json.dump(schedule, f)


def load_backup():
    """Загружает расписание из файла бэкапа."""
    global schedule
    if os.path.exists(backup_file):
        with open(backup_file, "r") as f:
            schedule = json.load(f)


async def handle_client(reader, writer):
    """Обрабатывает запрос клиента."""
    while True:
        data = await reader.read(1024)
        if not data:
            break

        message = data.decode()

        if message == "GET_SCHEDULE":
            async with schedule_lock:
                writer.write(str(schedule).encode())
                await writer.drain()
        else:
            # Обработка резервации
            login, ranges = message.split(":")
            ranges = eval(ranges)  # Преобразуем строку в список
            async with schedule_lock:
                for start_time, end_time in ranges:
                    for i, (s, e, counter, color) in enumerate(schedule):
                        if s == start_time and e == end_time:
                            counter += 1
                            if counter > 4:
                                color = 'orange'
                            if counter > 10:
                                color = 'red'
                            schedule[i] = (s, e, counter, color)
                            # Сохраняем данные о клиенте
                            if login not in clients_data:
                                clients_data[login] = []
                            clients_data[login].append((s, e))
                            break

                save_backup()  # Сохраняем обновлённое расписание в бэкап
                writer.write(str(schedule).encode())
                await writer.drain()

    writer.close()
    await writer.wait_closed()


async def update_schedule():
    """Очищает расписание каждые 10 секунд."""
    while True:
        await asyncio.sleep(15)
        async with schedule_lock:
            for i, (s, e, counter, color) in enumerate(schedule):
                if counter > 0:
                    schedule[i] = (s, e, 0, 'green')
            save_backup()  # Сохраняем обновления в бэкап


async def main():
    load_backup()  # Загружаем расписание из бэкапа при старте
    server = await asyncio.start_server(handle_client, 'localhost', 12345)
    asyncio.create_task(update_schedule())
    async with server:
        print("Основной сервер запущен на localhost:12345")
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
