# CustomerXPS - AI-Powered Support Ticket Analysis

Agentic system that automatically analyzes Freshdesk support tickets using AI embeddings to find similar past tickets and provide intelligent summaries.

## Features

- **Agentic System**: Autonomous Search and Summarization agents
- **Vector Search**: Find similar tickets using OpenAI embeddings
- **AI Summaries**: Generate customer-friendly insights using GPT/Claude
- **Auto-posting**: Summaries posted as public notes in Freshdesk
- **Webhook Support**: Automatic processing on new ticket creation 

## Project Structure

```
CustomerXPS POC/
├── src/                      # Core application
│   ├── agents.py             # Search & Summarization agents
│   ├── agent_workflow.py     # Multi-agent orchestration
│   ├── workflow.py           # Entry point
│   └── freshdesk_api.py      # Freshdesk API integration
│
├── scripts/                  # Setup scripts
│   ├── fetch_tickets.py      # Download tickets from Freshdesk
│   ├── generate_embeddings.py # Generate AI embeddings
│   └── insert_embeddings.py  # Load embeddings to database
│
├── api_server.py             # Webhook server
├── requirements.txt          # Python dependencies
├── .env                      # Configuration (not in git)
└── README.md
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```bash
# OpenAI
OPENAI_API_KEY=your_key

# Freshdesk
FRESHDESK_DOMAIN=https://your-domain.freshdesk.com
FRESHDESK_API_KEY=your_key

# Database
DB_NAME=freshdesk_embeddings
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# Optional: Anthropic Claude
ANTHROPIC_API_KEY=your_key
```

### 3. Setup Database

```sql
CREATE DATABASE freshdesk_embeddings;
\c freshdesk_embeddings
CREATE EXTENSION vector;

CREATE TABLE ticket_vectors (
    ticket_id INTEGER PRIMARY KEY,
    subject TEXT,
    description TEXT,
    summary TEXT,
    embedding vector(1536)
);
```

### 4. Load Initial Data

```bash
# Fetch tickets from Freshdesk
python scripts/fetch_tickets.py

# Generate embeddings
python scripts/generate_embeddings.py

# Load into database
python scripts/insert_embeddings.py
```

## Running

### Start Webhook Server

```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

### Start Cloudflared Tunnel

```bash
cloudflared tunnel --url http://localhost:8000
```

### Configure Freshdesk Webhook

1. Admin → Automations → Ticket Updates
2. Create rule: "When Ticket is Created"
3. Action: "Trigger Webhook"
4. URL: `https://your-cloudflared-url.com/webhook`
5. Method: POST, Encoding: JSON
6. Content:
   ```json
   {
     "ticket_id": {{ticket.id}},
     "description": "{{ticket.description}}"
   }
   ```

## How It Works

1. **New ticket created** → Webhook fired
2. **Search Agent** → Finds similar historical tickets
3. **Summarization Agent** → Generates customer-friendly summary
4. **Auto-post** → Summary added as public note in Freshdesk

## Requirements

- Python 3.8+
- PostgreSQL with pgvector
- Freshdesk account (free plan works)
- OpenAI API key
- Cloudflared for public webhook URL
