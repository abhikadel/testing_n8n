from src.agent_workflow import run_agent_workflow

def handle_user_query(ticket_id, query):
    """Process new ticket with agentic system"""
    print(f"\nProcessing ticket #{ticket_id} with Agentic System...")
    return run_agent_workflow(ticket_id, query)