#start_servers.py
import subprocess
from logger_setup import get_logger

logger = get_logger(__name__)


def start_server(ip, port, connected_ip, connected_port, my_number):
    """Запускает отдельный процесс для сервера."""
    return subprocess.Popen(["python", "server.py", ip, str(port), connected_ip, str(connected_port), str(my_number)])


def main():
    servers = [
        {"socket" : ("localhost", 20001), "connected_ip" : ("localhost", 20003), "my_number" : 1},
        {"socket" : ("localhost", 20003), "connected_ip" : ("localhost", 20004), "my_number" : 2},
        {"socket" : ("localhost", 20004), "connected_ip" : ("localhost", 20001), "my_number" : 3},
    ]

    processes = []
    try:
        for server in servers:
            ip, port = server["socket"]
            connected_ip, connected_port = server["connected_ip"]
            my_number = server["my_number"]
            process = start_server(ip, port, connected_ip, connected_port, my_number)
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
