from supabase import create_client
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def insert_vector(text, embedding, metadata):
    payload = {
        "content": text,
        "embedding": embedding,
        "file_id": metadata["file_id"],
        "userName": metadata["userName"],
        "userEmail": metadata["userEmail"],
        "createDate": metadata["createDate"],
    }

    supabase.table("documents").insert(payload).execute()
