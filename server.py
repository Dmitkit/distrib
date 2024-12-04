#server.py
import asyncio
import logging
import sys
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

schedule = [
    (9 , 10, 0, 'green'),
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

login_ranges = {}

schedule_lock = asyncio.Lock()

def add_range_for_login(login, range_value):
    if login not in login_ranges:
        login_ranges[login] = []
    
    # Check if the range already exists before adding
    if range_value not in login_ranges[login]:
        login_ranges[login].append(range_value)
        return True  # Range was added successfully
    return False    # Range already existed



async def handle_client(reader, writer):
    """Обрабатывает запросы клиентов."""
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

            if message == "GET_SERVER_DATA":
                async with schedule_lock:
                    server_data = {
                        "schedule": schedule,
                        "login_ranges": login_ranges
                    }
                writer.write(json.dumps(server_data).encode())
                await writer.drain()
                logger.info(f"Отправлены данные серверу расписания.")
            else:
                # Обработка резервации
                login, ranges = message.split(":", 1)
                add_range_for_login(login, ranges) # Добавляет диапазоны для логина
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
                                schedule[i] = (s, e, counter, color)
                                break
                    writer.write(str(True).encode())
                    await writer.drain()
                logger.info(f"Обработана резервация от клиента {login}: {ranges}")
                
    except Exception as e:
        logger.error(f"Ошибка при обработке клиента {client_addr}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()



async def main():
    if len(sys.argv) != 3:
        print("Использование: python server.py <IP> <PORT>")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    host_of_server_to_connect = sys.argv[3]
    port_of_server_to_connect = int(sys.argv[4])
    my_number_in_time_vector = int(sys.argv[5])

    server = await asyncio.start_server(handle_client, host, port)
    logger.info(f"Сервер запущен на {host}:{port}")

    # Запуск сервера
    async with server:
        await server.serve_forever()



if __name__ == "__main__":
    asyncio.run(main())
