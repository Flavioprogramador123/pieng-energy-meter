# app/routers/storage.py
from fastapi import APIRouter, HTTPException
from app.services.hybrid_storage import HybridStorage
from app.schemas import MeasurementCreate
from datetime import datetime
import os

router = APIRouter(prefix="/storage", tags=["storage"])

@router.get("/status")
async def get_storage_status():
    """Verificar status do armazenamento"""
    try:
        storage = HybridStorage()
        status = storage.get_storage_status()
        storage.close()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-gdrive")
async def test_google_drive():
    """Testar conexão com Google Drive"""
    try:
        storage = HybridStorage()
        
        if not storage.use_gdrive:
            return {
                "status": "error",
                "message": "Google Drive não configurado",
                "config": {
                    "credentials_file": os.getenv("GOOGLE_DRIVE_CREDENTIALS_FILE"),
                    "folder_id": os.getenv("GOOGLE_DRIVE_FOLDER_ID")
                }
            }
        
        # Testar conexão
        if storage.gdrive.test_connection():
            return {
                "status": "success",
                "message": "Conexão com Google Drive funcionando!",
                "config": {
                    "credentials_file": os.getenv("GOOGLE_DRIVE_CREDENTIALS_FILE"),
                    "folder_id": os.getenv("GOOGLE_DRIVE_FOLDER_ID")
                }
            }
        else:
            return {
                "status": "error",
                "message": "Falha na conexão com Google Drive"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-save")
async def test_save_measurement():
    """Testar salvamento de medição"""
    try:
        storage = HybridStorage()
        
        # Criar medição de teste
        success = storage.save_measurement(
            device_id=999,  # ID de teste
            metric="test_voltage",
            value=220.5,
            timestamp=datetime.now()
        )
        
        storage.close()
        
        if success:
            return {
                "status": "success",
                "message": "Medição de teste salva com sucesso!",
                "data": {
                    "device_id": 999,
                    "metric": "test_voltage",
                    "value": 220.5,
                    "timestamp": datetime.now().isoformat()
                }
            }
        else:
            return {
                "status": "error",
                "message": "Falha ao salvar medição de teste"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backup")
async def backup_to_google_drive():
    """Fazer backup de todos os dados para Google Drive"""
    try:
        storage = HybridStorage()
        
        if not storage.use_gdrive:
            storage.close()
            raise HTTPException(
                status_code=400, 
                detail="Google Drive não configurado"
            )
        
        success = storage.backup_to_gdrive()
        storage.close()
        
        if success:
            return {
                "status": "success",
                "message": "Backup realizado com sucesso!"
            }
        else:
            return {
                "status": "error",
                "message": "Falha no backup"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/restore")
async def restore_from_google_drive():
    """Restaurar dados do Google Drive"""
    try:
        storage = HybridStorage()
        
        if not storage.use_gdrive:
            storage.close()
            raise HTTPException(
                status_code=400, 
                detail="Google Drive não configurado"
            )
        
        success = storage.restore_from_gdrive()
        storage.close()
        
        if success:
            return {
                "status": "success",
                "message": "Dados restaurados com sucesso!"
            }
        else:
            return {
                "status": "error",
                "message": "Falha na restauração"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/measurements/{device_id}/{metric}")
async def get_measurements(device_id: int, metric: str, limit: int = 100):
    """Buscar medições usando storage híbrido"""
    try:
        storage = HybridStorage()
        measurements = storage.get_measurements(device_id, metric, limit)
        storage.close()
        
        return {
            "status": "success",
            "count": len(measurements),
            "data": measurements
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))