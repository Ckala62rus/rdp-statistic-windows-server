from fastapi import FastAPI
from app.api.v1 import rdp
from app.utils.logger import get_logger

log = get_logger(__name__)

app = FastAPI(
    title="RDP Sessions API",
    version="1.0.0",
    description="""
API для сбора и анализа статистики RDP-сессий пользователей на Windows-серверах.

- Получение отчёта по сессиям за выбранный период
- Группировка по пользователям и датам
- Интеграция с PowerShell через WinRM

**Автор:** Ваша команда
""",
    contact={
        "name": "RDP Stats Team",
        "email": "support@example.com"
    },
    docs_url="/docs",
    redoc_url="/redoc"
)

app.include_router(rdp.router, prefix="/api/v1/rdp", tags=["RDP Sessions"])


@app.on_event("startup")
def on_startup():
    log.info("FastAPI приложение успешно запущено!")


@app.get("/")
def root():
    log.info("Обращение к корневому эндпоинту API")
    return {"message": "RDP Sessions API", "docs": "/docs"}


@app.exception_handler(Exception)
def global_exception_handler(request, exc):
    log.error(f"Глобальная ошибка: {exc}")
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"error": "Internal Server Error", "detail": str(exc)})


if __name__ == "__main__":
    import uvicorn

    log.info("Запуск через __main__ (uvicorn)")
    uvicorn.run(app, host="0.0.0.0", port=8000)
