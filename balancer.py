#balancer.py

import asyncio

# Список серверов, с которыми работает балансировщик
servers = [
    ('localhost', 20001),
    ('localhost', 20003),
    ('localhost', 20004)
]
counter = 0
counter_lock = asyncio.Lock()


async def handle_client(reader, writer):
    """Обработка клиента, подключающегося к балансировщику."""
    global counter
    client_addr = writer.get_extra_info('peername')
    print(f"Клиент подключился: {client_addr}")

    async with counter_lock:
        # Выдаем сервер на основе текущего значения счетчика
        server_addr = servers[counter]
        counter = (counter + 1) % len(servers)  # Увеличиваем счетчик по модулю 3

    server_ip, server_port = server_addr
    writer.write(f"{server_ip}:{server_port}".encode())
    await writer.drain()

    print(f"Клиент {client_addr} перенаправлен на сервер {server_ip}:{server_port}")
    writer.close()
    await writer.wait_closed()


async def main():
    server = await asyncio.start_server(handle_client, 'localhost', 30000)
    print("Балансировщик запущен на localhost:30000")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
