from fastapi import FastAPI, BackgroundTasks, Request
from src.workflow import handle_user_query
from src.freshdesk_api import get_ticket_details
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


def process_ticket_async(ticket_id: int, description: str):
    """Process ticket with agentic system in background"""
    try:
        logger.info(f"Processing ticket #{ticket_id}")
        handle_user_query(ticket_id, description)
        logger.info(f"Completed ticket #{ticket_id}")
    except Exception as e:
        logger.error(f"Error processing ticket #{ticket_id}: {str(e)}")


@app.get("/")
def root():
    return {"status": "online"}


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Freshdesk webhook endpoint
    Configure in Freshdesk: https://your-cloudflared-url.com/webhook
    """
    try:
        payload = await request.json()
        logger.info(f"Webhook received: {payload}")
        
        # Extract ticket_id from various possible formats
        ticket_id = (
            payload.get("ticket_id") or 
            payload.get("freshdesk_webhook", {}).get("ticket_id") or
            payload.get("id")
        )
        
        if not ticket_id:
            logger.error("No ticket_id found in payload")
            return {"status": "error", "message": "Missing ticket_id"}
        
        # Fetch full ticket details from Freshdesk API
        try:
            ticket = get_ticket_details(ticket_id)
            description = ticket.get("description_text") or ticket.get("description") or "No description"
        except Exception as e:
            logger.warning(f"Could not fetch ticket: {e}")
            description = payload.get("description", "No description")
        
        # Process in background
        background_tasks.add_task(process_ticket_async, ticket_id, description)
        
        return {"status": "success", "ticket_id": ticket_id}
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}
