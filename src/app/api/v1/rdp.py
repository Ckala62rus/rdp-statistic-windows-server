from fastapi import APIRouter, HTTPException, Request, Query
from app.models.rdp import RdpSessionsResponse, RdpSession
from app.services.rdp_service import get_rdp_sessions
from app.utils.logger import get_logger

router = APIRouter()
log = get_logger(__name__)

example_response = {
    "start_date": "2025-07-01",
    "end_date": "2025-07-07",
    "total_sessions": 2,
    "sessions": [
        {
            "date": "2025-07-01",
            "user_id": "S-1-5-21-...",
            "username": "ivanov",
            "login_server": "server1",
            "logout_server": "server1",
            "login_time": "09:00:00",
            "logout_time": "18:00:00",
            "duration": "9:00:00"
        },
        {
            "date": "2025-07-02",
            "user_id": "S-1-5-21-...",
            "username": "ivanov",
            "login_server": "server2",
            "logout_server": "нет выхода",
            "login_time": "09:10:00",
            "logout_time": "23:59:59",
            "duration": "14:49:59 (нет выхода)"
        }
    ]
}

endpoint_description = """
Возвращает список сессий пользователей за указанный период.

**Параметры запроса:**
- `start_date` — Начальная дата периода отчёта (YYYY-MM-DD)
- `end_date` — Конечная дата периода отчёта (YYYY-MM-DD)

**Описание полей ответа:**
- `start_date` — Начальная дата периода отчёта (YYYY-MM-DD)
- `end_date` — Конечная дата периода отчёта (YYYY-MM-DD)
- `total_sessions` — Общее количество сессий в отчёте
- `sessions` — Список сессий пользователей за период
    - `date` — Дата сессии (день)
    - `user_id` — SID пользователя (уникальный идентификатор в Windows)
    - `username` — Имя пользователя (логин)
    - `login_server` — Сервер, на который был выполнен вход
    - `logout_server` — Сервер, с которого был выполнен выход (или "нет выхода", если не найден)
    - `login_time` — Время входа в сессию (часы:минуты:секунды)
    - `logout_time` — Время выхода из сессии (часы:минуты:секунды)
    - `duration` — Длительность сессии (часы:минуты:секунды, либо с пометкой "(нет выхода)")
"""

@router.get(
    "/sessions",
    response_model=RdpSessionsResponse,
    summary="Получить отчёт по RDP-сессиям",
    description=endpoint_description,
    response_description="JSON-отчёт по сессиям пользователей за период",
    tags=["RDP Sessions"],
    responses={
        200: {
            "description": "Успешный ответ с отчётом по сессиям",
            "content": {
                "application/json": {
                    "example": example_response
                }
            }
        },
        400: {"description": "Неверные параметры запроса"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
def get_sessions(
    start_date: str = Query(..., description="Начальная дата периода отчёта (YYYY-MM-DD)", example="2025-07-01"),
    end_date: str = Query(..., description="Конечная дата периода отчёта (YYYY-MM-DD)", example="2025-07-07")
):
    log.info(f"GET /sessions: {start_date} - {end_date}")
    try:
        sessions_data = get_rdp_sessions(start_date, end_date)
        sessions = [RdpSession(**session) for session in sessions_data]
        log.info(f"Отправлен отчёт: {len(sessions)} сессий")
        return RdpSessionsResponse(
            start_date=start_date,
            end_date=end_date,
            total_sessions=len(sessions),
            sessions=sessions
        )
    except Exception as e:
        log.error(f"Ошибка при формировании отчёта: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 