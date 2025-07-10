import os
from dotenv import load_dotenv
import winrm
import sys
import json
from datetime import datetime, timedelta
from collections import defaultdict
import re

# Функция для преобразования формата времени из PowerShell
# Пример: "/Date(1745060200298)/" -> datetime

def parse_ps_datetime(ps_date):
    match = re.search(r"\d+", ps_date)
    if match:
        timestamp = int(match.group(0)) // 1000
        return datetime.fromtimestamp(timestamp)
    return None

# Загрузка параметров
load_dotenv()
username = os.getenv('RDP_LOG_USERNAME')
password = os.getenv('RDP_LOG_PASSWORD')
domain = os.getenv('RDP_LOG_DOMAIN')
servers_str = os.getenv('RDP_SERVERS', '')

if not username or not password:
    print("Ошибка: не заданы параметры подключения (RDP_LOG_USERNAME, RDP_LOG_PASSWORD) в .env")
    sys.exit(1)

if not servers_str:
    print("Ошибка: не задан список серверов (RDP_SERVERS) в .env")
    sys.exit(1)

if domain:
    user = f"{domain}\\{username}"
else:
    user = username

# Список серверов для сбора статистики (из .env)
servers = [server.strip() for server in servers_str.split(',')]

# Дата для отчёта (можно задать диапазон)
report_date = "2025-07-07"  # YYYY-MM-DD - для одной даты
# Или диапазон дат:
# start_date = "2025-07-01"
# end_date = "2025-07-07"

# Определяем режим работы: одна дата или диапазон
single_date_mode = True  # True - одна дата, False - диапазон

if single_date_mode:
    # Режим одной даты
    start_date = report_date
    end_date = report_date
else:
    # Режим диапазона дат
    start_date = "2025-07-01"  # измените на нужную начальную дату
    end_date = "2025-07-07"    # измените на нужную конечную дату

# PowerShell-команда с фильтрацией по диапазону дат
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

# Сбор данных со всех серверов
all_data = []

for server in servers:
    print(f"Подключение к серверу {server}...")
    
    try:
        session = winrm.Session(server, auth=(user, password), transport='ntlm')
        result = session.run_ps(ps_command)
        
        if result.status_code != 0:
            print(f"Ошибка на сервере {server}:", result.std_err.decode(errors='ignore'))
            continue
            
        # Обработка результата
        try:
            data = json.loads(result.std_out.decode(errors='ignore'))
            if isinstance(data, list):
                # Добавляем информацию о сервере к каждому событию
                for event in data:
                    event['Server'] = server
                all_data.extend(data)
                print(f"Получено {len(data)} событий с сервера {server}")
            else:
                print(f"Неожиданный формат данных с сервера {server}")
                
        except Exception as e:
            print(f"Ошибка разбора JSON с сервера {server}:", e)
            continue
            
    except Exception as e:
        print(f"Ошибка подключения к серверу {server}:", e)
        continue

# Диагностика: выводим общее количество событий
if single_date_mode:
    print(f"Всего получено событий за {report_date}: {len(all_data)}")
else:
    print(f"Всего получено событий за период {start_date} - {end_date}: {len(all_data)}")

# Диагностика: выводим диапазон дат среди всех событий
all_dates = []
for event in all_data:
    dt = event.get("TimeCreated")
    if dt:
        match = re.search(r"\d+", dt)
        if match:
            timestamp = int(match.group(0)) // 1000
            all_dates.append(datetime.fromtimestamp(timestamp))
if all_dates:
    min_date = min(all_dates)
    max_date = max(all_dates)
    print(f"Минимальная дата: {min_date}")
    print(f"Максимальная дата: {max_date}")
else:
    print("Не удалось определить диапазон дат.")

# Группировка: (user, username) -> date -> list of events (объединяем данные с разных серверов)
sessions = defaultdict(lambda: defaultdict(list))
for event in all_data:
    server = event.get("Server", "unknown")
    user = str(event["User"])
    username = str(event.get("UserName", ""))
    dt = parse_ps_datetime(event["TimeCreated"])
    if not dt:
        continue
    date_str = dt.date().isoformat()
    # Группируем по пользователю, а не по серверу
    sessions[(user, username)][date_str].append({
        "datetime": dt,
        "type": event["Id"], # 21 - вход, 23 - выход
        "server": server
    })

# Формируем отчёт за выбранный период
report_rows = []
if single_date_mode:
    # Режим одной даты
    target_dates = [report_date]
else:
    # Режим диапазона дат - генерируем список дат
    from datetime import datetime, timedelta
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    target_dates = []
    current_dt = start_dt
    while current_dt <= end_dt:
        target_dates.append(current_dt.strftime("%Y-%m-%d"))
        current_dt += timedelta(days=1)

for (user, username), days in sessions.items():
    user_total_time = timedelta()
    user_sessions = []
    
    for target_date in target_dates:
        if target_date in days:
            events = days[target_date]
            # Сортируем события по времени
            events.sort(key=lambda x: x["datetime"])
            i = 0
            day_total_time = timedelta()
            
            while i < len(events):
                if events[i]["type"] == 21:  # вход
                    start_time = events[i]["datetime"]
                    start_server = events[i]["server"]
                    # ищем ближайший выход
                    end_time = None
                    end_server = None
                    for j in range(i+1, len(events)):
                        if events[j]["type"] == 23:
                            end_time = events[j]["datetime"]
                            end_server = events[j]["server"]
                            break
                    if end_time:
                        duration = end_time - start_time
                        day_total_time += duration
                        user_total_time += duration
                        user_sessions.append([
                            target_date, user, username,
                            start_server, end_server,
                            start_time.strftime("%H:%M:%S"),
                            end_time.strftime("%H:%M:%S"),
                            str(duration)
                        ])
                        i = j + 1
                    else:
                        # Нет выхода — считаем до конца дня
                        end_time = start_time.replace(hour=23, minute=59, second=59)
                        duration = end_time - start_time
                        day_total_time += duration
                        user_total_time += duration
                        user_sessions.append([
                            target_date, user, username,
                            start_server, "нет выхода",
                            start_time.strftime("%H:%M:%S"),
                            end_time.strftime("%H:%M:%S"),
                            str(duration) + " (нет выхода)"
                        ])
                        i += 1
                else:
                    i += 1
            
            # Итог по дню для пользователя
            if day_total_time:
                user_sessions.append([
                    target_date, user, username, "ВСЕ СЕРВЕРЫ", "", "", "Итого за день:", str(day_total_time)
                ])
    
    # Добавляем все сессии пользователя в отчёт
    report_rows.extend(user_sessions)
    
    # Итог по всему периоду для пользователя
    if user_total_time and not single_date_mode:
        report_rows.append([
            f"{start_date} - {end_date}", user, username, "ВСЕ СЕРВЕРЫ", "", "", "Итого за период:", str(user_total_time)
        ])

# Выводим в консоль отчёт
if single_date_mode:
    print(f"\nОтчёт за {report_date}:")
else:
    print(f"\nОтчёт за период {start_date} - {end_date}:")
    
print("Дата;UserId;Логин;Сервер входа;Сервер выхода;Вход;Выход;Длительность сессии;Итого за день")
if report_rows:
    for row in report_rows:
        print(";".join(str(x) for x in row))
else:
    if single_date_mode:
        print(f"Нет данных за {report_date}.")
    else:
        print(f"Нет данных за период {start_date} - {end_date}.") 