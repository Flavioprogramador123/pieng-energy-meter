# app/connectors/google_drive.py
import os
import json
import io
from datetime import datetime, timedelta
from typing import List, Dict, Optional

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:  # pacotes Google opcionais
    service_account = None  # type: ignore
    build = None  # type: ignore
    HttpError = Exception  # type: ignore
    GOOGLE_AVAILABLE = False

import pandas as pd

class GoogleDriveStorage:
    def __init__(self):
        self.credentials_file = os.getenv("GOOGLE_DRIVE_CREDENTIALS_FILE")
        self.folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        self.service = None

        if not GOOGLE_AVAILABLE:
            print("Google Drive API indisponivel (pacotes google nao instalados)")
            return

        # Tentar inicializar o serviço
        try:
            self.service = self._authenticate()
            print("Google Drive API inicializada com sucesso!")
        except Exception as e:
            print(f"Erro ao inicializar Google Drive API: {e}")
    
    def _authenticate(self):
        """Autenticar com Google Drive API"""
        if not GOOGLE_AVAILABLE:
            raise RuntimeError("Pacotes Google nao instalados")
        if not self.credentials_file:
            raise ValueError("GOOGLE_DRIVE_CREDENTIALS_FILE não configurado")
        
        if not self.folder_id:
            raise ValueError("GOOGLE_DRIVE_FOLDER_ID não configurado")
        
        # Verificar se o arquivo de credenciais existe
        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(f"Arquivo de credenciais não encontrado: {self.credentials_file}")
        
        credentials = service_account.Credentials.from_service_account_file(
            self.credentials_file,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        return build('drive', 'v3', credentials=credentials)
    
    def save_measurement(self, device_id: int, metric: str, value: float, timestamp: datetime = None):
        """Salvar medição no Google Drive"""
        if not self.service:
            print("❌ Google Drive API não inicializada")
            return False
        
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            # Criar dados da medição
            data = {
                'device_id': device_id,
                'metric': metric,
                'value': value,
                'timestamp': timestamp.isoformat()
            }
            
            # Nome do arquivo baseado na data
            filename = f"measurements_{timestamp.strftime('%Y-%m-%d')}.csv"
            
            # Verificar se arquivo já existe
            file_id = self._get_file_id(filename)
            
            if file_id:
                # Atualizar arquivo existente
                success = self._append_to_csv(file_id, data)
            else:
                # Criar novo arquivo
                success = self._create_csv_file(filename, data)
            
            if success:
                print(f"✅ Medição salva no Google Drive: {metric}={value}")
            return success
                
        except HttpError as error:
            print(f"❌ Erro ao salvar no Google Drive: {error}")
            return False
        except Exception as error:
            print(f"❌ Erro inesperado: {error}")
            return False
    
    def _get_file_id(self, filename: str) -> Optional[str]:
        """Buscar ID do arquivo no Google Drive"""
        try:
            results = self.service.files().list(
                q=f"name='{filename}' and parents in '{self.folder_id}'",
                fields="files(id, name)"
            ).execute()
            
            files = results.get('files', [])
            return files[0]['id'] if files else None
            
        except HttpError as error:
            print(f"❌ Erro ao buscar arquivo: {error}")
            return None
    
    def _create_csv_file(self, filename: str, data: Dict) -> bool:
        """Criar novo arquivo CSV"""
        try:
            # Criar CSV em memória
            df = pd.DataFrame([data])
            csv_content = df.to_csv(index=False)
            
            # Upload para Google Drive
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id]
            }
            
            media = io.BytesIO(csv_content.encode('utf-8'))
            
            self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            print(f"✅ Arquivo criado no Google Drive: {filename}")
            return True
            
        except Exception as error:
            print(f"❌ Erro ao criar arquivo: {error}")
            return False
    
    def _append_to_csv(self, file_id: str, data: Dict) -> bool:
        """Adicionar dados ao CSV existente"""
        try:
            # Baixar arquivo atual
            content = self.service.files().get_media(fileId=file_id).execute()
            
            # Converter para DataFrame
            existing_df = pd.read_csv(io.BytesIO(content))
            
            # Adicionar nova linha
            new_df = pd.DataFrame([data])
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            
            # Upload do arquivo atualizado
            csv_content = combined_df.to_csv(index=False)
            media = io.BytesIO(csv_content.encode('utf-8'))
            
            self.service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
            
            print(f"✅ Dados adicionados ao arquivo existente")
            return True
            
        except Exception as error:
            print(f"❌ Erro ao atualizar arquivo: {error}")
            return False
    
    def get_measurements(self, device_id: int, metric: str, days: int = 7) -> List[Dict]:
        """Buscar medições dos últimos N dias"""
        if not self.service:
            print("❌ Google Drive API não inicializada")
            return []
        
        try:
            measurements = []
            
            # Buscar arquivos dos últimos N dias
            for i in range(days):
                date = datetime.now() - timedelta(days=i)
                filename = f"measurements_{date.strftime('%Y-%m-%d')}.csv"
                
                file_id = self._get_file_id(filename)
                if file_id:
                    # Baixar e processar arquivo
                    content = self.service.files().get_media(fileId=file_id).execute()
                    df = pd.read_csv(io.BytesIO(content))
                    
                    # Filtrar por device_id e metric
                    filtered_df = df[
                        (df['device_id'] == device_id) & 
                        (df['metric'] == metric)
                    ]
                    
                    measurements.extend(filtered_df.to_dict('records'))
            
            print(f"✅ Encontradas {len(measurements)} medições no Google Drive")
            return measurements
            
        except HttpError as error:
            print(f"❌ Erro ao buscar medições: {error}")
            return []
        except Exception as error:
            print(f"❌ Erro inesperado: {error}")
            return []
    
    def test_connection(self) -> bool:
        """Testar conexão com Google Drive"""
        if not self.service:
            return False
        
        try:
            # Tentar listar arquivos na pasta
            results = self.service.files().list(
                q=f"parents in '{self.folder_id}'",
                fields="files(id, name)",
                pageSize=1
            ).execute()
            
            print("✅ Conexão com Google Drive testada com sucesso!")
            return True
            
        except Exception as error:
            print(f"❌ Erro ao testar conexão: {error}")
            return False