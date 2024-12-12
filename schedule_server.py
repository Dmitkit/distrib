#schedule_server.py
import asyncio
import json
import random
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
login_ranges = {}


def vectors_ordered(v1, v2):
    """Проверяет, могут ли два вектора быть упорядочены."""
    return all(a <= b for a, b in zip(v1, v2)) or all(a >= b for a, b in zip(v1, v2))


def build_partially_ordered_sets(vectors):
    """Создает частично упорядоченные множества, оставляя только минимальные векторы."""
    sorted_vectors = sorted(vectors)
    ordered_sets = []

    for v in sorted_vectors:
        added = False
        for ordered_set in ordered_sets:
            if all(vectors_ordered(v, existing_vector) for existing_vector in ordered_set):
                # Проверяем, является ли текущий вектор минимальным
                if all(not vectors_ordered(existing_vector, v) for existing_vector in ordered_set):
                    # Удаляем векторы, которые больше текущего
                    ordered_set[:] = [existing_vector for existing_vector in ordered_set if not vectors_ordered(existing_vector, v)]
                    ordered_set.append(v)
                added = True
                break
        if not added:
            ordered_sets.append([v])

    return ordered_sets


def select_randomly_from_sets(ordered_sets):
    """Выбираем случайное значение из минимальных векторов каждого множества."""
    selected = []
    for s in ordered_sets:
        first_value = min(s)
        selected.append(first_value)

    return random.choice(selected)


def generate_final_schedule(schedule, login_ranges):
    """Генерация итогового расписания с учетом частично упорядоченных множеств."""
    reserved_logins = set()
    final_schedule = []

    for s, e, _, _ in schedule:
        # Собираем всех кандидатов для текущего диапазона
        candidates = []
        for login, ranges in login_ranges.items():
            time_range_key = f"({s}, {e})"
            if time_range_key in ranges and login not in reserved_logins:
                candidates.append((login, ranges[time_range_key]))

        # Извлекаем векторы из кандидатов
        candidate_vectors = [vector for _, vector in candidates]

        if candidate_vectors:
            # Построение частично упорядоченных множеств
            ordered_sets = build_partially_ordered_sets(candidate_vectors)

            # Выбор минимального вектора из множеств
            selected_vector = select_randomly_from_sets(ordered_sets)

            # Найти логин, соответствующий выбранному вектору
            selected_login = next(
                login for login, vector in candidates if vector == selected_vector
            )
            reserved_logins.add(selected_login)
            final_schedule.append((s, e, selected_login))
        else:
            # Если кандидатов нет, слот остается свободным
            final_schedule.append((s, e, None))

    return final_schedule


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
    global schedule, login_ranges
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
                login_ranges = aggregated_login_ranges
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


async def periodic_schedule_generation():
    """Функция, которая раз в час генерирует итоговое расписание."""
    global schedule, login_ranges
    while True:
        try:
            async with schedule_lock:
                final_schedule = generate_final_schedule(schedule, login_ranges)
            logger.info(f"Итоговое расписание сгенерировано: {final_schedule}")            
            
        except Exception as e:
            logger.error(f"Ошибка при генерации итогового расписания: {e}")

        await asyncio.sleep(3600)


async def main():
    host = 'localhost'
    port = 20000

    server = await asyncio.start_server(handle_client, host, port)
    logger.info(f"Центральный сервер расписания запущен на {host}:{port}")
    asyncio.create_task(aggregate_schedules())    
    asyncio.create_task(periodic_schedule_generation())

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
