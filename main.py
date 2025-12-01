from flask import Flask, request, jsonify
from pathlib import Path
from drive_downloader import get_drive_service, get_latest_file_change_details, download_and_extract_text, TOKEN_PATH

app = Flask(__name__)

# --- Configuração de Filtros ---
# Lista de MIME Types permitidos para extração de texto
ALLOWED_MIME_TYPES = {
    'application/vnd.google-apps.document',                     # Google Docs (Transcrição Nativa)
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document', # Arquivos .docx (Microsoft Word)
    'application/pdf',                                          # Arquivos .pdf
    'text/plain',                                               # Arquivos .txt
}
# ------------------------------

# --- Funções de Persistência ---
def load_token():
    """Carrega o token da última página processada do arquivo."""
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, 'r') as f:
            return f.read().strip()
    return None

def save_token(token):
    """Salva o novo token da página inicial no arquivo."""
    with open(TOKEN_PATH, 'w') as f:
        f.write(token)
    print(f"| Token de rastreamento atualizado para: {token}")

def save_extracted_text_locally(text, file_id):
    """Salva o texto extraído em um arquivo local."""
    # Cria um nome de arquivo baseado no ID do Drive
    output_filename = f"extracted_text_{file_id}.txt"
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"\n| ✅ Texto SALVO localmente em: {output_filename}")
    except Exception as e:
        print(f"\n| ❌ Erro ao salvar o texto: {e}")
# --------------------------------


# --- Inicialização do Google Drive Service ---
try:
    DRIVE_SERVICE = get_drive_service()
    print("Serviço do Google Drive inicializado e pronto.")
except Exception as e:
    DRIVE_SERVICE = None
    print(f"ERRO FATAL: Falha ao inicializar o serviço do Google Drive. Erro: {e}")
# ---------------------------------------------


@app.route('/', methods=['GET'])
def index():
    return "Servidor de Notificações do Google Drive está ativo."


@app.route('/drive-webhook', methods=['POST'])
def handle_drive_notification():
    
    # 1. VALIDAÇÃO E EXTRAÇÃO DE INFORMAÇÕES CRUCIAIS
    resource_state = request.headers.get('X-Goog-Resource-State')
    
    print("================================================")
    print(f"----- Notificação Recebida | Estado: {resource_state} -----")
    
    if DRIVE_SERVICE is None:
        return jsonify({"status": "error", "message": "Drive service not initialized."}), 500

    if resource_state != 'change':
        print(f"Ignorando estado de recurso '{resource_state}'. Processando apenas 'change'.")
        return jsonify({"status": "ignored"}), 200

    # 2. CARREGA O ÚLTIMO TOKEN PROCESSADO
    last_processed_token = load_token()
    
    if not last_processed_token:
        print("| ❌ Falha: O token inicial não foi encontrado em 'last_processed_token.txt'. Execute configurar_webhook.py novamente.")
        return jsonify({"status": "error", "message": "Start token not found."}), 500
        
    print(f"| Token de Rastreamento Usado: {last_processed_token}")


    # 3. OBTÉM DETALHES DO ARQUIVO ALTERADO VIA API DE CHANGES
    file_id, mime_type, new_start_token = get_latest_file_change_details(DRIVE_SERVICE, last_processed_token)

    if not file_id:
        print("| ⚠️ Nenhum arquivo de alteração encontrado no histórico desde o último token. Ignorando.")
        if new_start_token and new_start_token != last_processed_token:
             save_token(new_start_token)
        return jsonify({"status": "no_file_found"}), 200

    print(f"| ID do Arquivo Detectado: {file_id}")
    print(f"| MIME Type Detectado: {mime_type}")

    # 4. FILTRA POR TIPOS DE ARQUIVO PERMITIDOS
    if mime_type in ALLOWED_MIME_TYPES:
        print(f"| ✅ Tipo de arquivo '{mime_type}' é permitido. Processando...")
        
        # --- CHAMADA PRINCIPAL: BAIXAR E EXTRAIR TEXTO ---
        extracted_text = download_and_extract_text(
            DRIVE_SERVICE, 
            file_id, 
            mime_type
        )
        
        # 5. EXIBIÇÃO E SALVAMENTO DO TEXTO EXTRAÍDO
        if extracted_text:
            text_preview = extracted_text[:200].replace('\n', ' ') + ('...' if len(extracted_text) > 200 else '')
            print("\n--- 📜 TEXTO EXTRAÍDO (Prévia) ---")
            print(text_preview)
            print("-----------------------------------")
            print(f"Log: Texto completo de {len(extracted_text)} caracteres extraído com sucesso.")
            
            # --- NOVO: SALVA O TEXTO ---
            save_extracted_text_locally(extracted_text, file_id)
            
        else:
            print("\n❌ Erro: Não foi possível extrair o texto do documento.")

    else:
        print(f"| 🚫 Tipo de arquivo '{mime_type}' não está na lista de processamento. Ignorando.")


    # 6. SALVAR O NOVO TOKEN DA PÁGINA INICIAL (MUITO IMPORTANTE!)
    if new_start_token and new_start_token != last_processed_token:
        save_token(new_start_token)


    # 7. RETORNO SUCESSO
    print("================================================")
    return jsonify({"status": "received_and_processed"}), 200

if __name__ == '__main__':
    print("Servidor rodando em http://127.0.0.1:5000/drive-webhook")
    app.run(port=5000, debug=True)