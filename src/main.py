#!/usr/bin/env python3
"""
FastAPI приложение для получения отчётов по RDP сессиям
"""

import os
import sys
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
import winrm
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# Добавляем текущую папку в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем рабочие функции
from fetch_rdp_sessions import get_rdp_data
from check_available_dates import check_available_dates

# Загружаем переменные окружения
try:
    load_dotenv()
except Exception as e:
    print(f"Предупреждение: Не удалось загрузить .env файл: {e}")

# Создаём FastAPI приложение
app = FastAPI(
    title="RDP Sessions Report API",
    version="1.0.0",
    description="API для получения отчётов по RDP сессиям"
)

# Модели для API
class RdpSessionRequest(BaseModel):
    start_date: str
    end_date: str

class RdpSession(BaseModel):
    date: str
    user_id: str
    username: str
    login_server: str
    logout_server: str
    login_time: str
    logout_time: str
    duration: str

class RdpSessionsResponse(BaseModel):
    start_date: str
    end_date: str
    total_sessions: int
    sessions: List[RdpSession]

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {"message": "RDP Sessions Report API", "version": "1.0.0"}

@app.get("/health")
async def health():
    """Проверка состояния API"""
    return {"status": "ok", "message": "API работает"}

@app.post("/api/sessions", response_model=RdpSessionsResponse)
async def get_sessions(request: RdpSessionRequest):
    """Получить отчёт по RDP сессиям"""
    try:
        sessions_data = get_rdp_data(request.start_date, request.end_date)
        
        # Преобразуем в модели Pydantic
        sessions = []
        for session_data in sessions_data:
            sessions.append(RdpSession(**session_data))
        
        return RdpSessionsResponse(
            start_date=request.start_date,
            end_date=request.end_date,
            total_sessions=len(sessions),
            sessions=sessions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/available-dates")
async def get_available_dates():
    """Получить доступные даты для отчётов"""
    try:
        dates = check_available_dates()
        return {"available_dates": dates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 