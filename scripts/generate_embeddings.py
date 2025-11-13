import json
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

with open("freshdesk_tickets.json", "r") as f:
    tickets = json.load(f)

def summarize(text):
    if not text:
        return ""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a technical support summarizer. Create concise summaries that preserve specific keywords, symptoms, error messages, and technical details. Focus on WHAT the problem is, not meta-descriptions."},
            {"role": "user", "content": f"Create a 2-3 sentence summary of this support ticket. Preserve specific keywords, error messages, and symptoms:\n\n{text}"}
        ]
    )
    return response.choices[0].message.content.strip()

def embed(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

for i, t in enumerate(tickets, 1):
    print(f"Processing ticket {i}/{len(tickets)}: #{t['id']} - {t.get('subject', '')[:50]}")
    
    # Get description from multiple possible fields
    desc = (
        t.get("description") or 
        t.get("description_text") or 
        t.get("structured_description") or 
        t.get("subject", "No content")
    )
    
    if len(desc) > 10:  # Only process if meaningful content
        t["summary"] = summarize(desc)
        t["embedding"] = embed(t["summary"])
        print(f"  ✅ Summary: {t['summary'][:80]}...")
    else:
        print(f"  ⚠️  Skipping - no meaningful content")
        t["summary"] = f"Ticket about: {t.get('subject', 'Unknown')}"
    t["embedding"] = embed(t["summary"])

with open("tickets_with_embeddings.json", "w") as f:
    json.dump(tickets, f, indent=2)

print("✅ Summaries + Embeddings generated.")
