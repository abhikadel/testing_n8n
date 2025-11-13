import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("FRESHDESK_API_KEY")
DOMAIN = os.getenv("FRESHDESK_DOMAIN")
URL = f"{DOMAIN}/api/v2/tickets?per_page=100"

response = requests.get(URL, auth=(API_KEY, "X"))
tickets = response.json()

# Save locally
with open("freshdesk_tickets.json", "w") as f:
    json.dump(tickets, f, indent=2)

print("Tickets downloaded:", len(tickets))