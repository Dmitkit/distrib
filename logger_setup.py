#logger_setup.py
import logging

def get_logger(name: str):
    """Создаёт логгер с базовой настройкой."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    return logging.getLogger(name)
