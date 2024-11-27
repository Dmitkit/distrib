#start_servers.py
import subprocess

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

        print("Все серверы запущены. Нажмите Ctrl+C для завершения.")
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        print("Остановка серверов...")
        for process in processes:
            process.terminate()
            process.wait()

if __name__ == "__main__":
    main()
