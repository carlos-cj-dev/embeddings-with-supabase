from drive_downloader import get_drive_service, TOKEN_PATH
import uuid

# --- Configurações ---
# A URL do webhook deve ser acessível publicamente (ex: via ngrok)
WEBHOOK_URL = 'https://6adb4e453f5f.ngrok-free.app/drive-webhook'
CHANNEL_ID = str(uuid.uuid4())
# ---------------------

def register_webhook():
    """
    Registra o webhook usando o método Changes.watch.
    """
    service = get_drive_service()

    # 1. Obter o token da página inicial de alterações
    start_page_token_res = service.changes().getStartPageToken().execute()
    start_page_token = start_page_token_res.get('startPageToken')
    
    if not start_page_token:
        print("Erro ao obter startPageToken.")
        return

    # 2. Salvar o token inicial para que main.py possa começar a rastrear.
    with open(TOKEN_PATH, 'w') as f:
        f.write(start_page_token)
    print(f"✅ Token inicial salvo em {TOKEN_PATH}.")


    # 3. Configurar o corpo da requisição 'watch'
    # O 'token' aqui é usado para reter o startPageToken
    request_body = {
        'id': CHANNEL_ID,
        'type': 'web_hook',
        'address': WEBHOOK_URL,
        'token': f'startPageToken={start_page_token}' 
    }

    try:
        print(f"Tentando registrar o Webhook no URL: {WEBHOOK_URL}...")
        
        response = service.changes().watch(
            pageToken=start_page_token,
            body=request_body,
            fields='expiration,id,resourceId,resourceUri'
        ).execute()

        print("✅ Webhook Registrado com Sucesso!")
        print(f"ID do Canal (Channel ID): {response.get('id')}")
        print(f"Expira em: {response.get('expiration')} ms")
        
        return response

    except Exception as e:
        print(f"❌ Erro ao registrar o Webhook: {e}")

if __name__ == '__main__':
    register_webhook()