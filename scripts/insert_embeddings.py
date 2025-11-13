import json
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)

cur = conn.cursor()

with open("tickets_with_embeddings.json", "r") as f:
    tickets = json.load(f)

for i, t in enumerate(tickets, 1):
    subject = t.get("subject", "")
    description = t.get("description", "") or t.get("structured_description", "")
    summary = t.get("summary", "")
    embedding = t.get("embedding", [])
    
    cur.execute("""
        INSERT INTO ticket_vectors (ticket_id, subject, description, summary, embedding)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (ticket_id) DO UPDATE SET
            subject = EXCLUDED.subject,
            description = EXCLUDED.description,
            summary = EXCLUDED.summary,
            embedding = EXCLUDED.embedding;
    """, (
        t["id"],
        subject,
        description,
        summary,
        embedding
    ))
    
    if i % 10 == 0:
        print(f"  Processed {i}/{len(tickets)} tickets...")

conn.commit()
cur.close()
conn.close()

print("✅ Successfully inserted into ticket_vectors table!")