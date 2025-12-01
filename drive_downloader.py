import io
import time
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload
from pathlib import Path
from docx import Document # IMPORTANTE: Adicione esta linha!

# --- Configurações Comuns ---
SCOPES = ['https://www.googleapis.com/auth/drive']
CREDENTIALS_FILE = 'credentials.json' # Arquivo JSON do Google Cloud Console
TOKEN_FILE = Path('token.json') # Arquivo que armazena o token
TOKEN_PATH = Path('last_processed_token.txt') # Caminho para o token de rastreamento de alterações
# ---------------------------

def get_drive_service():
    """
    Carrega credenciais salvas ou executa o fluxo de login se o token 
    não existir ou estiver expirado.
    Retorna o objeto de serviço do Google Drive.
    """
    creds = None
    
    # 1. Tenta carregar as credenciais salvas
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # 2. Se as credenciais existirem, mas expiraram, tenta renová-las
    if creds and creds.expired and creds.refresh_token:
        print("Token expirado. Tentando renovar...")
        time.sleep(1) 
        creds.refresh(Request())
        
    # 3. Se não houver credenciais válidas, inicia o fluxo de login
    if not creds or not creds.valid:
        print("Iniciando novo fluxo de autenticação...")
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        
    # 4. Salva as credenciais (novas ou renovadas)
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())
    
    print("✅ Autenticação Drive concluída.")
    return build('drive', 'v3', credentials=creds)

def get_latest_file_change_details(service, page_token):
    """
    Busca o ID e MIME Type do arquivo que disparou a notificação usando o Changes API.
    """
    try:
        response = service.changes().list(
            pageToken=page_token,
            fields='newStartPageToken, changes(fileId, file(mimeType))',
            restrictToMyDrive=True,
            pageSize=1
        ).execute()

        changes = response.get('changes', [])
        
        if changes:
            change = changes[0]
            file_id = change.get('fileId')
            file = change.get('file', {})
            mime_type = file.get('mimeType')
            new_token = response.get('newStartPageToken') 
            
            if file_id and mime_type:
                return file_id, mime_type, new_token 
        
    except Exception as e:
        print(f"❌ Erro ao buscar detalhes da mudança (Changes API): {e}")

    return None, None, None


def download_and_extract_text(service, file_id, file_mime_type):
    """
    Baixa o conteúdo do documento, adaptando o processamento ao tipo MIME.
    
    Para .docx, usa python-docx para extrair o texto.
    Para Docs Nativos, usa a exportação da API.
    """
    try:
        print(f"[DriveUtils] Tentando extrair texto de ID: {file_id}")

        # O fh (File Handle) é onde o conteúdo baixado será armazenado (na memória)
        fh = io.BytesIO()
        content = ""

        # 1. TRATAMENTO DE DOCUMENTOS NATIVOS DO GOOGLE (usa export_media)
        if file_mime_type.startswith('application/vnd.google-apps'):
            export_mime_type = 'text/plain'
            request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
            print(f"[DriveUtils] Usando export_media para Docs nativos ({file_mime_type})...")
            
            # Execução do Download (aqui o Drive já retorna texto puro)
            downloader = MediaIoBaseDownload(fh, request)
            while not downloader.next_chunk()[1]:
                pass
            fh.seek(0)
            content = fh.read().decode('utf-8', errors='ignore')

        # 2. TRATAMENTO DE ARQUIVOS .DOCX (usa get_media + python-docx)
        elif file_mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            request = service.files().get_media(fileId=file_id)
            print("[DriveUtils] Usando get_media + python-docx para arquivo DOCX...")
            
            # Execução do Download (baixa o arquivo binário .docx)
            downloader = MediaIoBaseDownload(fh, request)
            while not downloader.next_chunk()[1]:
                pass
            
            # Processamento com python-docx
            document = Document(fh)
            content = '\n'.join([paragraph.text for paragraph in document.paragraphs])
            
        # 3. TRATAMENTO DE ARQUIVOS TXT (usa get_media)
        elif file_mime_type == 'text/plain':
            request = service.files().get_media(fileId=file_id)
            print("[DriveUtils] Baixando diretamente arquivo TXT...")
            
            # Execução do Download (baixa o arquivo binário)
            downloader = MediaIoBaseDownload(fh, request)
            while not downloader.next_chunk()[1]:
                pass
            fh.seek(0)
            content = fh.read().decode('utf-8', errors='ignore')

        # 4. TRATAMENTO DE OUTROS TIPOS (PDF, etc.) - Atualmente não suportado sem biblioteca externa
        else:
             print(f"[DriveUtils] ⚠️ Processamento de '{file_mime_type}' ainda não implementado (requer lib externa).")
             return ""

        print(f"[DriveUtils] ✅ Extração de texto concluída. Tamanho: {len(content)} caracteres.")
        return content

    except ImportError:
        print("❌ [DriveUtils] Erro: A biblioteca 'python-docx' não está instalada. Execute 'pip install python-docx'.")
        return ""
    except Exception as e:
        print(f"❌ [DriveUtils] Erro ao baixar ou extrair texto do documento: {e}")
        return ""