import os
from dotenv import load_dotenv
import winrm
import json
from datetime import datetime, timedelta
from collections import defaultdict
import re
from app.utils.logger import get_logger

log = get_logger(__name__)


# Функция для преобразования формата времени из PowerShell
# Пример: "/Date(1745060200298)/" -> datetime
def parse_ps_datetime(ps_date):
    match = re.search(r"\d+", ps_date)
    if match:
        timestamp = int(match.group(0)) // 1000
        return datetime.fromtimestamp(timestamp)
    return None


def get_rdp_sessions(start_date: str, end_date: str) -> dict:
    load_dotenv()
    username = os.getenv('RDP_LOG_USERNAME')
    password = os.getenv('RDP_LOG_PASSWORD')
    domain = os.getenv('RDP_LOG_DOMAIN')
    servers_str = os.getenv('RDP_SERVERS', '')

    if not username or not password:
        log.error("Не заданы параметры подключения (RDP_LOG_USERNAME, RDP_LOG_PASSWORD) в .env")
        raise Exception("Не заданы параметры подключения (RDP_LOG_USERNAME, RDP_LOG_PASSWORD) в .env")
    if not servers_str:
        log.error("Не задан список серверов (RDP_SERVERS) в .env")
        raise Exception("Не задан список серверов (RDP_SERVERS) в .env")

    if domain:
        user = f"{domain}\\{username}"
    else:
        user = username

    servers = [server.strip() for server in servers_str.split(',')]
    log.info(f"Сбор статистики с серверов: {servers} за период {start_date} - {end_date}")

    ps_command = f'''
$dt1 = [datetime]"{start_date} 00:00:00"
$dt2 = [datetime]"{end_date} 23:59:59"

Get-WinEvent -LogName "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational" |
  Where-Object {{ 
    $_.Id -in 21,23 -and 
    $_.TimeCreated -ge $dt1 -and 
    $_.TimeCreated -le $dt2 
  }} |
  Select-Object TimeCreated, Id, @{{Name="User";Expression={{($_.Properties[1].Value)}}}}, @{{Name="UserName";Expression={{($_.Properties[0].Value)}}}} |
  Sort-Object TimeCreated | 
  ConvertTo-Json -Compress -Depth 4
'''

    all_data = []
    for server in servers:
        try:
            log.info(f"Подключение к серверу {server}...")
            session = winrm.Session(server, auth=(user, password), transport='ntlm')
            result = session.run_ps(ps_command)
            if result.status_code != 0:
                log.error(f"Ошибка на сервере {server}: {result.std_err.decode(errors='ignore')}")
                continue
            try:
                data = json.loads(result.std_out.decode(errors='ignore'))
                if isinstance(data, list):
                    for event in data:
                        event['Server'] = server
                    all_data.extend(data)
                    log.info(f"Получено {len(data)} событий с сервера {server}")
                else:
                    log.warning(f"Неожиданный формат данных с сервера {server}")
            except Exception as e:
                log.error(f"Ошибка разбора JSON с сервера {server}: {e}")
                continue
        except Exception as e:
            log.error(f"Ошибка подключения к серверу {server}: {e}")
            continue

    log.info(f"Всего получено событий: {len(all_data)}")

    # Группировка: (user, username) -> date -> list of events
    sessions = defaultdict(lambda: defaultdict(list))
    for event in all_data:
        server = event.get("Server", "unknown")
        user = str(event["User"])
        username = str(event.get("UserName", ""))
        dt = parse_ps_datetime(event["TimeCreated"])
        if not dt:
            continue
        date_str = dt.date().isoformat()
        sessions[(user, username)][date_str].append({
            "datetime": dt,
            "type": event["Id"],
            "server": server
        })

    # Формируем отчёт с группировкой по дате и username
    grouped = {}
    for (user, username), days in sessions.items():
        for date_str, events in days.items():
            if date_str not in grouped:
                grouped[date_str] = {}
            if username not in grouped[date_str]:
                grouped[date_str][username] = []
            events.sort(key=lambda x: x["datetime"])
            i = 0
            while i < len(events):
                if events[i]["type"] == 21:  # вход
                    start_time = events[i]["datetime"]
                    start_server = events[i]["server"]
                    end_time = None
                    end_server = None
                    for j in range(i + 1, len(events)):
                        if events[j]["type"] == 23:
                            end_time = events[j]["datetime"]
                            end_server = events[j]["server"]
                            break
                    if end_time:
                        duration = end_time - start_time
                        grouped[date_str][username].append({
                            "user_id": user,
                            "login_server": start_server,
                            "logout_server": end_server,
                            "login_time": start_time.strftime("%H:%M:%S"),
                            "logout_time": end_time.strftime("%H:%M:%S"),
                            "duration": str(duration)
                        })
                        i = j + 1
                    else:
                        end_time = start_time.replace(hour=23, minute=59, second=59)
                        duration = end_time - start_time
                        grouped[date_str][username].append({
                            "user_id": user,
                            "login_server": start_server,
                            "logout_server": "нет выхода",
                            "login_time": start_time.strftime("%H:%M:%S"),
                            "logout_time": end_time.strftime("%H:%M:%S"),
                            "duration": str(duration) + " (нет выхода)"
                        })
                        i += 1
                else:
                    i += 1
    log.info(
        f"Сформировано {sum(len(u) for d in grouped.values() for u in d.values())} сессий для отчёта (группировка)")
    return grouped
