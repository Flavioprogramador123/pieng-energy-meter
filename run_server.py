"""Entry point usado para empacotar o Energy Meter como executavel (PyInstaller).

Roda o mesmo FastAPI app que 'python -m uvicorn app.main:app', mas importando
o objeto app diretamente (em vez de uma import-string), o que e mais confiavel
dentro de um build congelado pelo PyInstaller.
"""
from app.main import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info",
        loop="asyncio",
        http="h11",
        ws="none",
    )
