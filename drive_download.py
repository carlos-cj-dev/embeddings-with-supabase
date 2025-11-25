import io
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# --- CONFIGURAÇÃO ---
# Se você mudar os escopos, delete o arquivo token.json para forçar nova autenticação.
SCOPES = ['https://www.googleapis.com/auth/drive']
# ID da pasta que você deseja baixar (veja o passo 3.1)
FOLDER_ID = '1QU1xjhvv5k_WAAI55IqaNIGYsUEJO42E'
# Nome do diretório onde os arquivos serão salvos localmente
DOWNLOAD_DIR = 'documentos_baixados'

def authenticate():
    """Realiza a autenticação e retorna o objeto de serviço do Drive."""
    creds = None
    # O arquivo token.json armazena os tokens de acesso e refresh do usuário.
    # Ele é criado automaticamente após a primeira autorização.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # Se não houver credenciais válidas, inicie o fluxo de login.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # O arquivo 'credentials.json' deve estar na mesma pasta.
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Salva as credenciais para futuras execuções
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    # Constrói o objeto de serviço para interagir com a API do Drive
    service = build('drive', 'v3', credentials=creds)
    return service

def download_files_from_folder(service, folder_id, download_path):
    """Lista e baixa todos os arquivos da pasta especificada."""
    
    # Cria o diretório de download se ele não existir
    os.makedirs(download_path, exist_ok=True)
    print(f"Buscando arquivos na pasta com ID: {folder_id}...")

    # Query para buscar arquivos dentro da pasta
    # O 'trashed = false' garante que apenas arquivos não deletados sejam buscados
    query = f"'{folder_id}' in parents and trashed = false"
    
    results = service.files().list(
        q=query,
        pageSize=100, # Limite de 100 resultados por página
        fields="nextPageToken, files(id, name, mimeType)").execute()
    items = results.get('files', [])

    if not items:
        print('Nenhum arquivo encontrado na pasta.')
        return
    
    print(f"Encontrados {len(items)} arquivos. Iniciando download...")
    
    for item in items:
        file_id = item['id']
        file_name = item['name']
        mime_type = item['mimeType']
        
        # Tratamento especial para documentos do Google (Docs, Sheets, Slides)
        # Eles precisam ser exportados para um formato padrão (PDF, XLSX, etc.)
        if mime_type.startswith('application/vnd.google-apps'):
            print(f"   [AVISO] '{file_name}' é um arquivo do Google. Exportando como PDF...")
            # Define o formato de exportação
            export_mime_type = 'application/pdf'
            # Remove a extensão do Google e adiciona .pdf
            # Ex: 'documento sem título' (Google Docs) -> 'documento sem título.pdf'
            local_filename = f"{os.path.splitext(file_name)[0]}.pdf"
            
            request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
        else:
            # Para arquivos normais (PDF, DOCX, JPG, etc.)
            local_filename = file_name
            request = service.files().get_media(fileId=file_id)

        # Monta o caminho completo para salvar o arquivo
        local_filepath = os.path.join(download_path, local_filename)

        try:
            # Baixa o conteúdo do arquivo
            fh = io.FileIO(local_filepath, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                if status:
                    # Opcional: Mostrar progresso
                    # print("Download %d%%." % int(status.progress() * 100))
                    pass
            
            print(f"   ✅ Baixado: {local_filename}")

        except Exception as e:
            print(f"   ❌ ERRO ao baixar '{local_filename}': {e}")


if __name__ == '__main__':
    # 1. Autentica e obtém o serviço do Drive
    drive_service = authenticate()
    
    # 2. Executa a função de download
    download_files_from_folder(drive_service, FOLDER_ID, DOWNLOAD_DIR)
    
    print("\n--- Processo concluído ---")
    print(f"Os arquivos foram salvos na pasta: {DOWNLOAD_DIR}/")