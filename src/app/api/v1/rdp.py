from fastapi import APIRouter, HTTPException, Request, Query
from app.models.rdp import RdpSessionsGroupedResponse
from app.services.rdp_service import get_rdp_sessions
from app.utils.logger import get_logger

router = APIRouter()
log = get_logger(__name__)

example_grouped_response = {
    "start_date": "2025-07-01",
    "end_date": "2025-07-03",
    "dates": {
        "2025-07-01": {
            "ivanov": [
                {
                    "user_id": "S-1-5-21-...",
                    "login_server": "server1",
                    "logout_server": "server1",
                    "login_time": "09:00:00",
                    "logout_time": "18:00:00",
                    "duration": "9:00:00"
                }
            ],
            "petrov": [
                {
                    "user_id": "S-1-5-21-...",
                    "login_server": "server2",
                    "logout_server": "server2",
                    "login_time": "10:00:00",
                    "logout_time": "17:00:00",
                    "duration": "7:00:00"
                }
            ]
        },
        "2025-07-02": {
            "ivanov": [
                {
                    "user_id": "S-1-5-21-...",
                    "login_server": "server2",
                    "logout_server": "нет выхода",
                    "login_time": "09:10:00",
                    "logout_time": "23:59:59",
                    "duration": "14:49:59 (нет выхода)"
                }
            ]
        },
        "2025-07-03": {
            "petrov": [
                {
                    "user_id": "S-1-5-21-...",
                    "login_server": "server1",
                    "logout_server": "server1",
                    "login_time": "08:30:00",
                    "logout_time": "16:30:00",
                    "duration": "8:00:00"
                }
            ]
        }
    }
}

endpoint_grouped_description = """
Возвращает сгруппированный отчёт по сессиям пользователей за указанный период.

**Параметры запроса:**
- `start_date` — Начальная дата периода отчёта (YYYY-MM-DD)
- `end_date` — Конечная дата периода отчёта (YYYY-MM-DD)

**Структура ответа:**
- `start_date` — Начальная дата периода отчёта (YYYY-MM-DD)
- `end_date` — Конечная дата периода отчёта (YYYY-MM-DD)
- `dates` — словарь, где ключ — дата (YYYY-MM-DD), значение — словарь username → список сессий пользователя за этот день
    - `username` — имя пользователя (логин)
        - список сессий пользователя за день, каждая сессия содержит:
            - `user_id` — SID пользователя (уникальный идентификатор в Windows)
            - `login_server` — Сервер, на который был выполнен вход
            - `logout_server` — Сервер, с которого был выполнен выход (или "нет выхода", если не найден)
            - `login_time` — Время входа в сессию (часы:минуты:секунды)
            - `logout_time` — Время выхода из сессии (часы:минуты:секунды)
            - `duration` — Длительность сессии (часы:минуты:секунды, либо с пометкой "(нет выхода)")

**Пример ответа:**
```
{
  "start_date": "2025-07-01",
  "end_date": "2025-07-03",
  "dates": {
    "2025-07-01": {
      "ivanov": [
        {
          "user_id": "S-1-5-21-...",
          "login_server": "server1",
          "logout_server": "server1",
          "login_time": "09:00:00",
          "logout_time": "18:00:00",
          "duration": "9:00:00"
        }
      ],
      "petrov": [
        {
          "user_id": "S-1-5-21-...",
          "login_server": "server2",
          "logout_server": "server2",
          "login_time": "10:00:00",
          "logout_time": "17:00:00",
          "duration": "7:00:00"
        }
      ]
    },
    "2025-07-02": {
      "ivanov": [
        {
          "user_id": "S-1-5-21-...",
          "login_server": "server2",
          "logout_server": "нет выхода",
          "login_time": "09:10:00",
          "logout_time": "23:59:59",
          "duration": "14:49:59 (нет выхода)"
        }
      ]
    },
    "2025-07-03": {
      "petrov": [
        {
          "user_id": "S-1-5-21-...",
          "login_server": "server1",
          "logout_server": "server1",
          "login_time": "08:30:00",
          "logout_time": "16:30:00",
          "duration": "8:00:00"
        }
      ]
    }
  }
}
```
"""


@router.get(
    "/sessions",
    response_model=RdpSessionsGroupedResponse,
    summary="Получить сгруппированный отчёт по RDP-сессиям",
    description=endpoint_grouped_description,
    response_description="JSON-отчёт по сессиям пользователей, сгруппированный по дате и username",
    tags=["RDP Sessions"],
    responses={
        200: {
            "description": "Успешный ответ с отчётом по сессиям (группировка)",
            "content": {
                "application/json": {
                    "example": example_grouped_response
                }
            }
        },
        400: {"description": "Неверные параметры запроса"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
def get_sessions(
        start_date: str = Query(..., description="Начальная дата периода отчёта (YYYY-MM-DD)", example="2025-07-01"),
        end_date: str = Query(..., description="Конечная дата периода отчёта (YYYY-MM-DD)", example="2025-07-03")
):
    log.info(f"GET /sessions: {start_date} - {end_date}")
    try:
        grouped = get_rdp_sessions(start_date, end_date)
        return RdpSessionsGroupedResponse(
            start_date=start_date,
            end_date=end_date,
            dates=grouped
        )
    except Exception as e:
        log.error(f"Ошибка при формировании отчёта: {e}")
        raise HTTPException(status_code=500, detail=str(e))
