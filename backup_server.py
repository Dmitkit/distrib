#backup_server
import asyncio

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

schedule_lock = asyncio.Lock()

PRIMARY_SERVER_ADDRESS = ('localhost', 20001)


async def handle_client(reader, writer):
    """Обрабатывает запросы клиентов."""
    while True:
        data = await reader.read(512)
        if not data:
            break

        message = data.decode()

        if message == "GET_SCHEDULE":
            async with schedule_lock:
                writer.write(str(schedule).encode())
                await writer.drain()
        else:
            login, ranges = message.split(":", 1)
            ranges = eval(ranges)
            async with schedule_lock:
                for start_time, end_time in ranges:
                    for i, (s, e, counter, color) in enumerate(schedule):
                        if s == start_time and e == end_time:
                            counter += 1
                            if counter > 4:
                                color = 'orange'
                            if counter > 10:
                                color = 'red'

                            # Обновляем версию
                            schedule[i] = (s, e, counter, color)
                            break
                writer.write(str(schedule).encode())
                await writer.drain()

    writer.close()
    await writer.wait_closed()


async def sync_with_primary():
    """Периодическая синхронизация с основным сервером."""
    global schedule
    while True:
        await asyncio.sleep(1)
        try:
            reader, writer = await asyncio.open_connection(*PRIMARY_SERVER_ADDRESS)
            writer.write("GET_SCHEDULE".encode())
            await writer.drain()
            data = await reader.read(512)
            if data:
                remote_schedule = eval(data.decode())
                async with schedule_lock:
                    schedule = remote_schedule
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            print(f"Не удалось синхронизироваться с основным сервером: {e}")


async def main():
    server = await asyncio.start_server(handle_client, 'localhost', 20002)
    asyncio.create_task(sync_with_primary())
    async with server:
        print("Резервный сервер запущен на localhost:20002")
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
