from pydantic import BaseModel, Field
from typing import List, Dict


class RdpSession(BaseModel):
    user_id: str = Field(..., description="SID пользователя (уникальный идентификатор в Windows)")
    login_server: str = Field(..., description="Сервер, на который был выполнен вход")
    logout_server: str = Field(...,
                               description="Сервер, с которого был выполнен выход (или 'нет выхода', если не найден)")
    login_time: str = Field(..., description="Время входа в сессию (часы:минуты:секунды)")
    logout_time: str = Field(..., description="Время выхода из сессии (часы:минуты:секунды)")
    duration: str = Field(..., description="Длительность сессии (часы:минуты:секунды, либо с пометкой '(нет выхода)')")


class RdpSessionsGroupedResponse(BaseModel):
    start_date: str = Field(..., description="Начальная дата периода отчёта (YYYY-MM-DD)")
    end_date: str = Field(..., description="Конечная дата периода отчёта (YYYY-MM-DD)")
    dates: Dict[str, Dict[str, List[RdpSession]]] = Field(..., description="Словарь дата -> username -> список сессий")


# Оставляем старые модели для обратной совместимости
class RdpSessionRequest(BaseModel):
    start_date: str = Field(..., description="Начальная дата периода отчёта (YYYY-MM-DD)")
    end_date: str = Field(..., description="Конечная дата периода отчёта (YYYY-MM-DD)")


class RdpSessionsResponse(BaseModel):
    start_date: str = Field(..., description="Начальная дата периода отчёта (YYYY-MM-DD)")
    end_date: str = Field(..., description="Конечная дата периода отчёта (YYYY-MM-DD)")
    total_sessions: int = Field(..., description="Общее количество сессий в отчёте")
    sessions: List[RdpSession] = Field(..., description="Список сессий пользователей за период")
