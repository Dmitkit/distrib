import asyncio
import json
import os

# Инициализация расписания
schedule = []
backup_file = "schedule_backup.json"
clients_data = {}
schedule_lock = asyncio.Lock()

# Порт основного сервера
primary_server_port = 20001
backup_server_port = 20002

def load_backup():
    """Загружает расписание из файла бэкапа."""
    global schedule
    if os.path.exists(backup_file):
        with open(backup_file, "r") as f:
            schedule = json.load(f)
    else:
        # Если файла бэкапа нет, создаём пустое расписание
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


def save_backup():
    """Сохраняет расписание в файл бэкапа."""
    with open(backup_file, "w") as f:
        json.dump(schedule, f, indent=4)


async def handle_client(reader, writer):
    """Обрабатывает запрос клиента."""
    while True:
        data = await reader.read(512)
        if not data:
            break

        message = data.decode()

        if message == "GET_SCHEDULE":
            async with schedule_lock:
                writer.write(json.dumps(schedule).encode())
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
                            if login not in clients_data:
                                clients_data[login] = []
                            clients_data[login].append((s, e))
                            break

                # Сохраняем обновленное расписание в бэкап
                save_backup()

                writer.write(json.dumps(schedule).encode())
                await writer.drain()

    writer.close()
    await writer.wait_closed()


async def update_schedule():
    """Очищает расписание каждые n секунд."""
    while True:
        await asyncio.sleep(15)
        async with schedule_lock:
            for i, (s, e, counter, color) in enumerate(schedule):
                if counter > 0:
                    schedule[i] = (s, e, 0, 'green')

            # Сохраняем обновленное расписание в бэкап после очистки
            save_backup()


async def start_primary_server():
    """Пытается запустить основной сервер."""
    try:
        # Запускаем основной сервер
        server = await asyncio.start_server(handle_client, 'localhost', primary_server_port)
        async with server:
            print(f"Основной сервер запущен на localhost:{primary_server_port}")
            await server.serve_forever()
    except Exception as e:
        print(f"Ошибка запуска основного сервера: {e}")
        print("Попытка перезапуска через 5 секунд...")
        await asyncio.sleep(5)  # Ждем 5 секунд перед повторной попыткой
        await start_primary_server()  # Перезапуск основного сервера


async def start_backup_server():
    """Запускает резервный сервер."""
    server = await asyncio.start_server(handle_client, 'localhost', backup_server_port)
    asyncio.create_task(update_schedule())
    async with server:
        print(f"Резервный сервер запущен на localhost:{backup_server_port}")
        await server.serve_forever()


async def main():
    load_backup()  # Загружаем расписание из бэкапа

    # Запускаем основной сервер в фоновом потоке
    asyncio.create_task(start_primary_server())

    # Запускаем резервный сервер
    await start_backup_server()


if __name__ == "__main__":
    asyncio.run(main())
