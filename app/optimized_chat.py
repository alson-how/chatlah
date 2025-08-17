# app/optimized_chat.py
from typing import Dict
from app.slots import ConversationState
from app.rag_assist import maybe_rag_line
from app.late_capture import parse_all
from app.database import get_merchant_config, save_consumer_data, get_conversation_session, save_conversation_session

# Global session storage - in production, use Redis or database
SESSION: Dict[str, ConversationState] = {}

def get_state(user_id: str) -> ConversationState:
    """Get conversation state for a user."""
    return SESSION.setdefault(user_id, ConversationState())

def set_state(user_id: str, state: ConversationState):
    """Set conversation state for a user."""
    SESSION[user_id] = state

def handle_merchant_chat(thread_id: str, user_text: str, merchant_id: int) -> dict:
    """
    Optimized merchant chat handler using the new modular architecture.
    
    Args:
        thread_id: Unique conversation thread ID
        user_text: User's message
        merchant_id: ID of the merchant configuration to use
        
    Returns:
        dict: Response with answer, status, collected_data, next_field
    """
    try:
        # Get merchant configuration
        merchant_config = get_merchant_config(merchant_id)
        if not merchant_config:
            return {"error": f"Merchant {merchant_id} not found"}
        
        # Load conversation state from database
        session_data = get_conversation_session(thread_id)
        if session_data:
            state = ConversationState()
            collected_data = session_data.get('collected_data', {})
            state.name = collected_data.get('name')
            state.phone = collected_data.get('phone')
            state.location = collected_data.get('location')
            state.style = collected_data.get('style')
            state.scope = collected_data.get('scope')
        else:
            state = ConversationState()
        
        # Process conversation using enhanced modules
        # 1) Late capture any fields from user message
        parsed = parse_all(user_text)
        if parsed["name"] and not state.name:         state.name = parsed["name"]
        if parsed["phone"] and not state.phone:       state.phone = parsed["phone"]
        if parsed["style"] and not state.style:       state.style = parsed["style"]
        if parsed["location"] and not state.location: state.location = parsed["location"]
        
        # 2) Try to answer with enhanced RAG (includes intent detection and portfolio preview)
        rag_response = maybe_rag_line(user_text)
        if rag_response:
            reply = rag_response
            # Continue conversation flow after answering
            next_slot = state.next_slot()
            if next_slot.name != 'NONE':
                from app.api import next_missing_after_portfolio
                follow_up = next_missing_after_portfolio(state)
                if follow_up:
                    reply += f"\n{follow_up}"
        else:
            # 3) Normal conversation flow - ask for next missing field
            next_slot = state.next_slot()
            if next_slot.name == 'NONE':
                reply = "Thank you! I have all the information I need."
            else:
                from app.slots import QUESTIONS
                reply = QUESTIONS[next_slot]
        
        new_state = state
        
        # Convert state back to collected data
        collected_data = {
            'name': new_state.name,
            'phone': new_state.phone,
            'location': new_state.location,
            'style': new_state.style,
            'scope': new_state.scope
        }
        
        # Remove None values
        collected_data = {k: v for k, v in collected_data.items() if v is not None}
        
        # Determine status and next field
        next_slot = new_state.next_slot()
        if next_slot.name == 'NONE':
            status = 'complete'
            next_field = None
            
            # Save final consumer data
            save_consumer_data(merchant_id, thread_id, collected_data, 'complete')
            
            # Generate completion message with merchant info
            merchant_name = merchant_config.get('name', 'our team')
            company_name = merchant_config.get('company', 'the company')
            
            summary_parts = []
            for field_id, value in collected_data.items():
                if value:
                    field_name = field_id.replace('_', ' ').title()
                    summary_parts.append(f"{field_name}: {value}")
            
            summary = ", ".join(summary_parts)
            reply = f"Perfect! Thank you. I have all the details I need - {summary}. {merchant_name} from {company_name} will follow up with you soon."
            
        else:
            status = 'collecting'
            next_field = next_slot.name.lower()
            
            # Save current progress (convert field name to index)
            field_index = 0 if next_field == 'name' else 1 if next_field == 'phone' else 2 if next_field == 'location' else 3 if next_field == 'style' else 4
            save_conversation_session(thread_id, merchant_id, field_index, collected_data, 'active')
        
        return {
            "answer": reply,
            "status": status,
            "collected_data": collected_data,
            "next_field": next_field
        }
        
    except Exception as e:
        return {"error": f"Error processing chat: {str(e)}"}

def handle_incoming(user_id: str, user_text: str) -> str:
    """
    Legacy compatibility handler for the original architecture.
    """
    state = get_state(user_id)
    reply, new_state = craft_reply(user_text, state)
    set_state(user_id, new_state)
    return reply