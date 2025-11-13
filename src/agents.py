from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv
import os
import psycopg2
from openai import OpenAI

load_dotenv()

# Initialize LLMs
openai_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

# Claude as fallback/alternative
claude_llm = ChatAnthropic(
    model="claude-3-5-sonnet-20241022",
    temperature=0,
    api_key=os.getenv("ANTHROPIC_API_KEY")
) if os.getenv("ANTHROPIC_API_KEY") else None

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_keywords(query: str) -> list:
    """Extract meaningful keywords from query, removing stop words"""
    stop_words = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
        'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
        'to', 'was', 'will', 'with', 'this', 'but', 'they', 'have', 'had',
        'what', 'when', 'where', 'who', 'which', 'why', 'how', 'can', 'could',
        'would', 'should', 'may', 'might', 'must', 'shall', 'am', 'i', 'my'
    }
    
    # Split and clean
    words = query.lower().split()
    keywords = [
        word.strip('.,!?;:()[]{}"\'-') 
        for word in words 
        if len(word) > 2 and word.lower() not in stop_words
    ]
    
    return keywords[:10]  # Limit to top 10 keywords

def vector_search_tool(query: str) -> str:
    """Hybrid search: Semantic (embeddings) + Keyword (full-text) search"""
    try:
        # Extract keywords for text search
        keywords = extract_keywords(query)
        keyword_query = ' | '.join(keywords) if keywords else ''  # OR logic for better matching
        
        print(f"Search keywords: {keywords}")
        
        # Generate embedding for semantic search
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        query_embedding = response.data[0].embedding
        query_vector = "[" + ",".join(str(x) for x in query_embedding) + "]"
        
        # Connect to database
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        cur = conn.cursor()
        
        # HYBRID SEARCH QUERY
        cur.execute("""
            WITH semantic_search AS (
                SELECT 
                    ticket_id,
                    subject,
                    summary,
                    (1 - (embedding <=> %s::vector)) AS semantic_score,
                    0 AS keyword_score
                FROM ticket_vectors
                ORDER BY embedding <=> %s::vector
                LIMIT 10
            ),
            keyword_search AS (
                SELECT 
                    ticket_id,
                    subject,
                    summary,
                    0 AS semantic_score,
                    ts_rank(search_vector, to_tsquery('english', %s)) AS keyword_score
                FROM ticket_vectors
                WHERE search_vector @@ to_tsquery('english', %s)
                ORDER BY keyword_score DESC
                LIMIT 10
            ),
            combined AS (
                SELECT 
                    COALESCE(s.ticket_id, k.ticket_id) AS ticket_id,
                    COALESCE(s.subject, k.subject) AS subject,
                    COALESCE(s.summary, k.summary) AS summary,
                    COALESCE(s.semantic_score, 0) AS semantic_score,
                    COALESCE(k.keyword_score, 0) AS keyword_score
                FROM semantic_search s
                FULL OUTER JOIN keyword_search k ON s.ticket_id = k.ticket_id
            )
            SELECT 
                ticket_id,
                subject,
                summary,
                semantic_score,
                keyword_score,
                (semantic_score * 0.7 + keyword_score * 30) AS combined_score
            FROM combined
            WHERE (semantic_score > 0 OR keyword_score > 0)
            ORDER BY combined_score DESC
            LIMIT 5;
        """, (query_vector, query_vector, keyword_query, keyword_query))
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        if not results:
            return "No similar tickets found in the database."
        
        # Format results with detailed scores
        formatted = "Found similar tickets:\n\n"
        for ticket_id, subject, summary, semantic_score, keyword_score, combined_score in results:
            semantic_pct = round(semantic_score * 100, 2)
            keyword_pct = round(keyword_score * 100, 2) if keyword_score else 0
            combined_pct = round(combined_score, 2)
            
            formatted += f"Ticket #{ticket_id}: {subject}\n"
            formatted += f"Summary: {summary}\n"
            formatted += f"Semantic: {semantic_pct}% | Keywords: {keyword_pct}% | Combined: {combined_pct}%\n\n"
        
        return formatted
        
    except Exception as e:
        return f"Error searching tickets: {str(e)}"

def analyze_ticket_context_tool(ticket_info: str) -> str:
    """Analyze ticket context (category, urgency, sentiment)"""
    try:
        llm = claude_llm if claude_llm else openai_llm
        
        prompt = f"""Analyze this ticket and provide:
1. Issue Category (e.g., billing, technical, account)
2. Urgency Level (low/medium/high)
3. Customer Sentiment (positive/neutral/negative)
4. Key Problem Statement (one sentence)

Ticket Info:
{ticket_info}

Respond in this format:
Category: [category]
Urgency: [level]
Sentiment: [sentiment]
Problem: [statement]
"""
        
        response = llm.invoke(prompt)
        return response.content
        
    except Exception as e:
        return f"Error analyzing context: {str(e)}"


def get_freshdesk_ticket_tool(ticket_id: str) -> str:
    """Fetch full ticket details from Freshdesk API"""
    try:
        import requests
        from requests.auth import HTTPBasicAuth
        
        url = f"{os.getenv('FRESHDESK_DOMAIN')}/api/v2/tickets/{ticket_id}"
        response = requests.get(
            url, 
            auth=HTTPBasicAuth(os.getenv("FRESHDESK_API_KEY"), "X")
        )
        response.raise_for_status()
        
        ticket = response.json()
        return f"""Ticket #{ticket['id']}
Subject: {ticket.get('subject', 'N/A')}
Description: {ticket.get('description_text', 'N/A')}
Status: {ticket.get('status', 'N/A')}
Priority: {ticket.get('priority', 'N/A')}
Created: {ticket.get('created_at', 'N/A')}
"""
    except Exception as e:
        return f"Error fetching ticket: {str(e)}"


class SearchAgent:
    """Autonomous agent that finds similar tickets"""
    
    def __init__(self):
        self.llm = openai_llm
        self.tools = {
            'vector_search': vector_search_tool,
            'analyze_context': analyze_ticket_context_tool,
            'get_ticket': get_freshdesk_ticket_tool
        }
    
    def invoke(self, input_data):
        """Execute search agent workflow"""
        query = input_data.get("input", "")
        
        print(f"\nSearch Agent: Analyzing query...") 
        print(f"Query: '{query[:100]}...'")
        
        # Agent decision-making: Search for similar tickets
        print("\nSearch Agent: Executing vector search...")
        search_results = vector_search_tool(query)
        
        # Print the similar tickets found
        print("\n" + "="*70)
        print("SIMILAR TICKETS FOUND:")
        print("="*70)
        print(search_results)
        print("="*70)
        
        # Agent decision-making: Analyze context if useful
        if "error" not in search_results.lower() and len(search_results) > 100:
            print("\nSearch Agent: Analyzing ticket context...")
            context_analysis = analyze_ticket_context_tool(query)
            output = f"{search_results}\n\nContext Analysis:\n{context_analysis}"
        else:
            output = search_results
        
        return {"output": output}

def create_search_agent():
    """Create and return Search Agent"""
    return SearchAgent()


def summarize_with_openai(context: str) -> str:
    """Generate summary using OpenAI GPT"""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful support assistant. Write brief, conversational responses. No markdown formatting, bullet points, or special characters. Keep responses under 150 words."},
                {"role": "user", "content": f"""Based on these similar past tickets, write a brief helpful message (3-4 sentences max):

{context}

Include: what the issue is, what usually helps, and 1-2 simple next steps. Write naturally like talking to a person."""}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error with OpenAI: {str(e)}"

def summarize_with_claude(context: str) -> str:
    """Generate summary using Anthropic Claude"""
    if not claude_llm:
        return "Claude API key not configured. Use OpenAI instead."
    
    try:
        response = claude_llm.invoke(f"""Based on these similar past tickets, write a brief helpful message (3-4 sentences max):

{context}

Include: what the issue is, what usually helps, and 1-2 simple next steps. Write naturally like talking to a person. No markdown, bullet points, or special formatting. Keep it under 150 words.""")
        return response.content
    except Exception as e:
        return f"Error with Claude: {str(e)}"

def format_customer_message(summary: str) -> str:
    """Format summary into customer-friendly language"""
    prompt = f"""Rewrite this as a simple, friendly support message:

{summary}

Rules:
- Maximum 4-5 sentences
- No markdown, asterisks, bullets, or special formatting
- Write like a helpful person, not a robot
- Be warm but brief
- Plain text only"""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error formatting: {str(e)}"

class SummarizationAgent:
    """Autonomous agent that creates customer-friendly summaries"""
    
    def __init__(self):
        self.llm = claude_llm if claude_llm else openai_llm
        self.tools = {
            'summarize_openai': summarize_with_openai,
            'summarize_claude': summarize_with_claude,
            'format_customer': format_customer_message
        }
    
    def invoke(self, input_data):
        """Execute summarization agent workflow"""
        query = input_data.get("input", "")
        
        print(f"\nSummarization Agent: Processing input...")
        
        # Agent decision-making: Choose appropriate LLM
        if claude_llm and len(query) > 500:
            print("Summarization Agent: Using Claude for analysis...")
            summary = summarize_with_claude(query)
        else:
            print("Summarization Agent: Using OpenAI for summarization...")
            summary = summarize_with_openai(query)
        
        # Use summary directly - it's already customer-friendly from the new prompt
        print("\n" + "="*70)
        print("Generated Summary:")
        print("="*70)
        print(summary)
        print("="*70)
        
        return {"output": summary}

def create_summarization_agent():
    """Create and return Summarization Agent"""
    return SummarizationAgent()


def get_agents():
    """Initialize and return both agents"""
    search_agent = create_search_agent()
    summarization_agent = create_summarization_agent()
    
    return {
        "search_agent": search_agent,
        "summarization_agent": summarization_agent
    }

