#schedule_server.py
import asyncio
import json
from logger_setup import get_logger

logger = get_logger(__name__)

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
    (19, 20, 0, 'green'),
]

connected_servers = [
    ('localhost', 20001),
    ('localhost', 20002),
    ('localhost', 20003),
]

schedule_lock = asyncio.Lock()


async def fetch_server_data(ip, port):
    try:
        reader, writer = await asyncio.open_connection(ip, port)
        writer.write(b"GET_SERVER_DATA")
        await writer.drain()

        data = await reader.read(2048)
        writer.close()
        await writer.wait_closed()

        return json.loads(data.decode())
    except Exception as e:
        logger.error(f"Ошибка запроса к серверу {ip}:{port}: {e}")
        return None
    

async def aggregate_schedules():
    global schedule
    while True:
        try:
            # Параллельный сбор данных от всех серверов
            server_data_list = await asyncio.gather(
                *(fetch_server_data(ip, port) for ip, port in connected_servers),
                return_exceptions=True
            )

            # Обработка данных (исключая ошибки)
            new_schedule = [(s, e, 0, 'green') for s, e, _, _ in schedule]
            aggregated_login_ranges = {}

            for server_data in server_data_list:
                if isinstance(server_data, dict):  # Проверяем, что данные получены успешно
                    for i, (s, e, count, color) in enumerate(server_data["schedule"]):
                        _, _, current_count, _ = new_schedule[i]
                        total_count = current_count + count
                        new_color = (
                            'red' if total_count > 10 else
                            'orange' if total_count > 4 else
                            'green'
                        )
                        new_schedule[i] = (s, e, total_count, new_color)

                    # Объединение данных о логинах
                    for login, ranges in server_data["login_ranges"].items():
                        if login not in aggregated_login_ranges:
                            aggregated_login_ranges[login] = ranges
                        else:
                            aggregated_login_ranges[login].extend(
                                r for r in ranges if r not in aggregated_login_ranges[login]
                            )

            # Обновляем расписание и логины
            async with schedule_lock:
                schedule[:] = new_schedule
                logger.info("Обновлено общее расписание.")
        except Exception as e:
            logger.error(f"Ошибка во время агрегации расписания: {e}")

        await asyncio.sleep(1)


async def handle_client(reader, writer):
    """Обрабатывает запросы клиентов на получение расписания."""
    client_addr = writer.get_extra_info('peername')
    logger.info(f"Клиент подключился: {client_addr}")

    try:
        while True:
            data = await reader.read(512)
            if not data:
                logger.info(f"Клиент {client_addr} отключился.")
                break

            message = data.decode()
            logger.info(f"Получено сообщение от клиента {client_addr}: {message}")

            if message == "GET_SCHEDULE":
                async with schedule_lock:
                    writer.write(str(schedule).encode())
                    await writer.drain()
                logger.info(f"Отправлено расписание клиенту {client_addr}")
    except Exception as e:
        logger.error(f"Ошибка при обработке клиента {client_addr}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def main():
    host = 'localhost'
    port = 20000

    server = await asyncio.start_server(handle_client, host, port)
    logger.info(f"Центральный сервер расписания запущен на {host}:{port}")
    asyncio.create_task(aggregate_schedules())

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
