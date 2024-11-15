import asyncio

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

# Хранение данных о клиентах
clients_data = {}
schedule_lock = asyncio.Lock()


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

                writer.write(str(schedule).encode())
                await writer.drain()

    writer.close()
    await writer.wait_closed()

async def update_schedule():
    while True:
        await asyncio.sleep(10)  # Очищаем каждые 10 секунд
        for i, (s, e, counter, color) in enumerate(schedule):
            if counter > 4:
                schedule[i] = (s, e, 0, 'green')



async def main():
    server = await asyncio.start_server(handle_client, 'localhost', 12345)
    asyncio.create_task(update_schedule())   
    async with server:
        print("Сервер запущен на localhost:12345")
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
