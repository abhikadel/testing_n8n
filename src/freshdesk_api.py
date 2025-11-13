import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import os

load_dotenv()

FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN")
API_KEY = os.getenv("FRESHDESK_API_KEY")

def get_ticket_details(ticket_id):
    url = f"{FRESHDESK_DOMAIN}/api/v2/tickets/{ticket_id}"
    response = requests.get(url, auth=HTTPBasicAuth(API_KEY, "X"))
    response.raise_for_status()
    return response.json()

def add_public_note(ticket_id, message):
    url = f"{FRESHDESK_DOMAIN}/api/v2/tickets/{ticket_id}/notes"
    payload = {
        "body": message,
        "private": False  # Visible to customer & agent
    }
    response = requests.post(url, json=payload, auth=HTTPBasicAuth(API_KEY, "X"))
    response.raise_for_status()
    result = response.json()
    
    # Log the note creation
    print(f"\nNote created successfully!")
    print(f"   Note ID: {result.get('id')}")
    print(f"   Created at: {result.get('created_at')}")
    print(f"   Private: {result.get('private')}")
    
    return result
