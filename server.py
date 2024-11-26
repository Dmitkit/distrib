import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Список расписания с поддержкой DVVS
schedule = [
    (9, 10, 0, 'green', {}),
    (10, 11, 0, 'green', {}),
    (11, 12, 0, 'green', {}),
    (12, 13, 0, 'green', {}),
    (13, 14, 0, 'green', {}),
    (14, 15, 0, 'green', {}),
    (15, 16, 0, 'green', {}),
    (16, 17, 0, 'green', {}),
    (17, 18, 0, 'green', {}),
    (18, 19, 0, 'green', {}),
    (19, 20, 0, 'green', {})
]

schedule_lock = asyncio.Lock()


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

            if message == "GET_SCHEDULE":
                async with schedule_lock:
                    writer.write(str(schedule).encode())
                    await writer.drain()
                logger.info(f"Отправлено расписание клиенту {client_addr}")
            else:
                # Обработка резервации
                login, node_id, ranges = message.split(":", 2)
                ranges = eval(ranges)
                async with schedule_lock:
                    for start_time, end_time in ranges:
                        for i, (s, e, counter, color, versions) in enumerate(schedule):
                            if s == start_time and e == end_time:
                                counter += 1
                                if counter > 4:
                                    color = 'orange'
                                if counter > 10:
                                    color = 'red'
                                versions[node_id] = versions.get(node_id, 0) + 1
                                schedule[i] = (s, e, counter, color, versions)
                                break
                    writer.write(str(schedule).encode())
                    await writer.drain()
                logger.info(f"Обработана резервация от клиента {client_addr}: {ranges}")
    except Exception as e:
        logger.error(f"Ошибка при обработке клиента {client_addr}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def merge_schedules(local_schedule, remote_schedule):
    """Слияние расписаний между узлами."""
    merged_schedule = []
    async with schedule_lock:
        for local, remote in zip(local_schedule, remote_schedule):
            if local[:2] == remote[:2]:  # Проверяем, совпадают ли временные диапазоны
                s, e, local_count, local_color, local_versions = local
                _, _, remote_count, remote_color, remote_versions = remote

                # Объединяем версии
                combined_versions = {**local_versions, **remote_versions}
                # Берём максимальный счётчик и цвет
                merged_count = max(local_count, remote_count)
                merged_color = local_color if merged_count == local_count else remote_color

                merged_schedule.append((s, e, merged_count, merged_color, combined_versions))
    return merged_schedule


async def sync_with_peer(peer_address):
    """Синхронизация с другим сервером."""
    try:
        reader, writer = await asyncio.open_connection(*peer_address)
        writer.write("GET_SCHEDULE".encode())
        await writer.drain()
        data = await reader.read(512)
        if data:
            remote_schedule = eval(data.decode())
            global schedule
            schedule = await merge_schedules(schedule, remote_schedule)
        writer.close()
        await writer.wait_closed()
    except Exception as e:
        logger.error(f"Не удалось синхронизироваться с {peer_address}: {e}")


async def periodic_sync():
    """Периодически синхронизуирует расписание с другими узлами."""
    while True:
        await asyncio.sleep(10)
        await sync_with_peer(('localhost', 20002))


async def main():
    server = await asyncio.start_server(handle_client, 'localhost', 20001)
    logger.info("Сервер запущен на localhost:20001")

    asyncio.create_task(periodic_sync())

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
