import logging
import sys

LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
)

# Создаём корневой логгер
logger = logging.getLogger("rdp_app")
logger.setLevel(logging.INFO)

# Хендлер для вывода в stdout (Docker-friendly)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(LOG_FORMAT))

# Добавляем хендлер только если его ещё нет
if not logger.hasHandlers():
    logger.addHandler(handler)

# Функция для получения логгера в других модулях
get_logger = lambda name=None: logger if name is None else logger.getChild(name) 