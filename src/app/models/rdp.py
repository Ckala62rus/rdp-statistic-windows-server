from pydantic import BaseModel, Field
from typing import List

class RdpSessionRequest(BaseModel):
    start_date: str = Field(..., description="Начальная дата периода отчёта (YYYY-MM-DD)")
    end_date: str = Field(..., description="Конечная дата периода отчёта (YYYY-MM-DD)")

class RdpSession(BaseModel):
    date: str = Field(..., description="Дата сессии (день)")
    user_id: str = Field(..., description="SID пользователя (уникальный идентификатор в Windows)")
    username: str = Field(..., description="Имя пользователя (логин)")
    login_server: str = Field(..., description="Сервер, на который был выполнен вход")
    logout_server: str = Field(..., description="Сервер, с которого был выполнен выход (или 'нет выхода', если не найден)")
    login_time: str = Field(..., description="Время входа в сессию (часы:минуты:секунды)")
    logout_time: str = Field(..., description="Время выхода из сессии (часы:минуты:секунды)")
    duration: str = Field(..., description="Длительность сессии (часы:минуты:секунды, либо с пометкой '(нет выхода)')")

class RdpSessionsResponse(BaseModel):
    start_date: str = Field(..., description="Начальная дата периода отчёта (YYYY-MM-DD)")
    end_date: str = Field(..., description="Конечная дата периода отчёта (YYYY-MM-DD)")
    total_sessions: int = Field(..., description="Общее количество сессий в отчёте")
    sessions: List[RdpSession] = Field(..., description="Список сессий пользователей за период") 