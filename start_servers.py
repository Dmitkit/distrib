#start_servers.py
import subprocess
from logger_setup import get_logger

logger = get_logger(__name__)


def start_server(ip, port):
    """Запускает отдельный процесс для сервера."""
    return subprocess.Popen(["python", "server.py", ip, str(port)])


def main():
    servers = [
        ("localhost", 20001),
        ("localhost", 20003),
        ("localhost", 20004),
    ]

    processes = []
    try:
        for ip, port in servers:
            process = start_server(ip, port)
            processes.append(process)

        logger.info("Все серверы запущены. Нажмите Ctrl+C для завершения.")

        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        logger.info("Остановка серверов...")
        for process in processes:
            process.terminate()
            process.wait()
        logger.info("Все серверы остановлены.")


if __name__ == "__main__":
    main()
