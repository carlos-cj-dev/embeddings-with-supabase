from fastapi import FastAPI, Request
from drive import download_file, extract_text
from embeddings import generate_embeddings
from supabase_client import insert_vector
from datetime import datetime

app = FastAPI()

@app.post("/webhook/drive")
async def drive_webhook(request: Request):
    data = await request.json()

    file_id = data["id"]
    user_name = data["user"]["displayName"]
    user_email = data["user"]["email"]
    created_time = data["timeCreated"]

    file_path = download_file(file_id)

    text = extract_text(file_path)

    vector = generate_embeddings(text)

    insert_vector(
        text=text,
        embedding=vector,
        metadata={
            "file_id": file_id,
            "userName": user_name,
            "userEmail": user_email,
            "createDate": created_time
        }
    )

    return {"status": "processed", "file": file_id}
