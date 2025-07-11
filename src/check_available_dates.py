import os
from dotenv import load_dotenv
import winrm
import sys
import json
from datetime import datetime, timedelta
import re

# Функция для преобразования формата времени из PowerShell
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

# Список серверов для проверки (из .env)
servers = [server.strip() for server in servers_str.split(',')]

# PowerShell-команда для получения всех событий RDP
ps_command = '''
Get-WinEvent -LogName "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational" |
  Where-Object { $_.Id -in 21,23 } |
  Select-Object TimeCreated, Id, @{Name="User";Expression={($_.Properties[1].Value)}}, @{Name="UserName";Expression={($_.Properties[0].Value)}} |
  Sort-Object TimeCreated | 
  ConvertTo-Json -Compress -Depth 4
'''

print("Проверка доступных дат в журналах RDP-событий...")
print("=" * 60)

for server in servers:
    print(f"\nСервер: {server}")
    print("-" * 40)
    
    try:
        session = winrm.Session(server, auth=(user, password), transport='ntlm')
        result = session.run_ps(ps_command)
        
        if result.status_code != 0:
            print(f"❌ Ошибка подключения к серверу {server}:", result.std_err.decode(errors='ignore'))
            continue
            
        # Обработка результата
        try:
            data = json.loads(result.std_out.decode(errors='ignore'))
            if isinstance(data, list) and data:
                # Анализируем даты
                dates = []
                for event in data:
                    dt = parse_ps_datetime(event.get("TimeCreated", ""))
                    if dt:
                        dates.append(dt)
                
                if dates:
                    min_date = min(dates)
                    max_date = max(dates)
                    total_days = (max_date - min_date).days
                    
                    print(f"📊 Всего событий: {len(data)}")
                    print(f"📅 Первое событие: {min_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"📅 Последнее событие: {max_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"📈 Период: {total_days} дней")
                    
                    # Проверяем последние 30 дней
                    thirty_days_ago = datetime.now() - timedelta(days=30)
                    recent_events = [d for d in dates if d >= thirty_days_ago]
                    print(f"📊 Событий за последние 30 дней: {len(recent_events)}")
                    
                    # Проверяем последние 90 дней
                    ninety_days_ago = datetime.now() - timedelta(days=90)
                    older_events = [d for d in dates if d >= ninety_days_ago]
                    print(f"📊 Событий за последние 90 дней: {len(older_events)}")
                    
                else:
                    print("❌ Не удалось определить даты событий")
            else:
                print("❌ Нет данных или неожиданный формат")
                
        except Exception as e:
            print(f"❌ Ошибка разбора данных: {e}")
            
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")

print("\n" + "=" * 60)
print("💡 Рекомендации:")
print("• Для получения статистики за период до 30 дней - проблем нет")
print("• Для периода 30-90 дней - зависит от настроек журнала")
print("• Для периода более 90 дней - может потребоваться настройка политики очистки")
print("• Используйте фильтрацию по дате в скрипте для получения нужного периода") 