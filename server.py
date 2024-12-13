#server.py
import asyncio
import sys
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

login_ranges = {}
# login_ranges = {
#     "user1": {
#         (9, 10) : (1, 0, 0), 
#         (11, 12) : (1, 0, 0), 
#     },
#     "user2": {
#         (10, 11) : (1, 1, 0),
#         (12, 13) : (1, 1, 0),
#     }
# }

vector = [0, 0, 0]

schedule_lock = asyncio.Lock()


async def forward_to_other_server():
    """Отправляет вектор на другой сервер с пометкой 'VECTOR:'."""
    try:
        # Преобразуем вектор в строку и добавляем префикс 'VECTOR:'
        vector_str = "VECTOR:" + ",".join(map(str, vector))

        # Устанавливаем соединение с другим сервером
        reader, writer = await asyncio.open_connection(next_server_host, next_server_port)

        # Отправляем строку
        writer.write(vector_str.encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()

        logger.info(f"{host}:{port} Вектор времени отправлен на сервер {next_server_host}:{next_server_port}")
    except Exception as e:
        logger.error(f"{host}:{port} Ошибка при отправке вектора времени на другой сервер: {e}")


async def send_vector_periodically():
    """Периодически отправляет вектор на другой сервер."""
    global vector
    while True:
        await forward_to_other_server()
        # vector[my_number - 1] += 1
        await asyncio.sleep(1)


def merge_vectors(received_vector):
    """Объединяет два вектора времени, возвращая максимальные значения поэлементно."""
    return [max(vector[i], received_vector[i]) for i in range(len(vector))]


def add_range_for_login(login, ranges):
    """Добавляет диапазоны для указанного логина и обновляет векторные часы для диапазона, если они еще не существуют."""
    global vector

    if login not in login_ranges:
        login_ranges[login] = {}

    # Присваиваем один вектор для всех диапазонов
    for range_value in ranges:
        # Проверяем, существует ли данный диапазон, если нет - добавляем его с текущим вектором
        if range_value not in login_ranges[login]:
            login_ranges[login][range_value] = vector

    # Увеличиваем вектор после добавления всех диапазонов
    vector[my_number - 1] += 1


async def handle_connection(reader, writer):
    """Обрабатывает входящие подключения (от клиентов или других серверов)."""
    global vector
    client_addr = writer.get_extra_info('peername')
    logger.debug(f"{host}:{port} Подключение: {client_addr}")

    try:
        while True:
            data = await reader.read(512)
            if not data:
                logger.debug(f"{host}:{port} Отключение: {client_addr}")
                break

            message = data.decode()
            logger.debug(f"{host}:{port} Получено сообщение от {client_addr}: {message}")

            if message.startswith("VECTOR:"):
                # Извлекаем вектор времени после префикса "VECTOR:"
                vector_data = message[len("VECTOR:"):].strip()
                received_vector = list(map(int, vector_data.split(",")))
                vector = merge_vectors(received_vector)
                logger.info(f"{host}:{port} Полученен вектор времени: {received_vector}. Обновлённый вектор времени: {vector}")
            elif message == "GET_SERVER_DATA":
                async with schedule_lock:
                    server_data = {
                        "schedule": schedule,
                        "login_ranges": {k: {str(key): value for key, value in v.items()} for k, v in login_ranges.items()},
                        # "vector": vector
                    }
                writer.write(json.dumps(server_data).encode())
                await writer.drain()
                logger.info(f"{host}:{port} Отправлены данные серверу расписания.")
            elif message.startswith("CLIENT:"):
                message = message[len("CLIENT:"):].strip()
                # Обработка резервации
                login, ranges = message.split(":", 1)
                ranges = eval(ranges)
                add_range_for_login(login, ranges) # Добавляет диапазоны для логина

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
                logger.info(f"{host}:{port} Обработана резервация от клиента {login}: {ranges}")

    except Exception as e:
        logger.error(f"{host}:{port} Ошибка при обработке {client_addr}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def start_server(host, port):
    """Запускает сервер для обработки всех запросов (от клиентов и серверов)."""
    server = await asyncio.start_server(handle_connection, host, port)
    logger.info(f"Сервер запущен на {host}:{port}")
    async with server:
        await server.serve_forever()


async def main():
    if len(sys.argv) != 6:
        logger.info("Использование: python server.py <IP> <PORT> <IP_SERVER_TO_CONNECT> <PORT_SERVER_TO_CONNECT> <MY_NUMBER_IN_TIME_VECTOR>")
        sys.exit(1)

    global host, port, next_server_host, next_server_port, my_number
    host = sys.argv[1]
    port = int(sys.argv[2])
    next_server_host = sys.argv[3]
    next_server_port = int(sys.argv[4])
    my_number = int(sys.argv[5])

    await asyncio.gather(
        start_server(host, port),
        send_vector_periodically()
    )


if __name__ == "__main__":
    asyncio.run(main())
