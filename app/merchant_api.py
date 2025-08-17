# app/merchant_api.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from app.database import create_merchant, get_merchant_config, get_conversation_session, update_conversation_session
from app.merchant_config import MerchantFieldConfig, MERCHANT_TEMPLATES, ConversationFlow
import json

router = APIRouter()

class MerchantCreateRequest(BaseModel):
    name: str
    company: str
    template: Optional[str] = None  # Use predefined template
    fields_config: Optional[List[Dict[str, Any]]] = None  # Custom fields
    conversation_tone: str = "professional"

class MerchantResponse(BaseModel):
    id: int
    name: str
    company: str
    fields_config: List[Dict[str, Any]]
    conversation_tone: str

class ChatRequest(BaseModel):
    thread_id: str
    user_message: str
    merchant_id: int

class ChatResponse(BaseModel):
    answer: str
    status: str  # 'collecting', 'complete'
    collected_data: Dict[str, str]
    next_field: Optional[str]

@router.post("/merchants", response_model=MerchantResponse)
async def create_merchant_endpoint(request: MerchantCreateRequest):
    """Create a new merchant with custom field configuration."""
    
    try:
        # Use template if provided, otherwise use custom fields
        if request.template and request.template in MERCHANT_TEMPLATES:
            fields_config = [field.to_dict() for field in MERCHANT_TEMPLATES[request.template]]
        elif request.fields_config:
            fields_config = request.fields_config
        else:
            raise HTTPException(status_code=400, detail="Either template or fields_config must be provided")
        
        merchant_id = create_merchant(
            name=request.name,
            company=request.company,
            fields_config=fields_config,
            tone=request.conversation_tone
        )
        
        return MerchantResponse(
            id=merchant_id,
            name=request.name,
            company=request.company,
            fields_config=fields_config,
            conversation_tone=request.conversation_tone
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating merchant: {str(e)}")

@router.get("/merchants/{merchant_id}", response_model=MerchantResponse)
async def get_merchant(merchant_id: int):
    """Get merchant configuration by ID."""
    
    config = get_merchant_config(merchant_id)
    if not config:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    return MerchantResponse(
        id=config['id'],
        name=config['name'],
        company=config['company'],
        fields_config=config['fields_config'],
        conversation_tone=config['tone']
    )

@router.get("/templates")
async def get_merchant_templates():
    """Get available merchant templates."""
    
    templates = {}
    for template_name, fields in MERCHANT_TEMPLATES.items():
        templates[template_name] = {
            'name': template_name.replace('_', ' ').title(),
            'fields': [field.to_dict() for field in fields]
        }
    
    return templates

@router.post("/chat", response_model=ChatResponse)
async def merchant_chat(request: ChatRequest):
    """Optimized chat handler using modular architecture."""
    
    try:
        from app.optimized_chat import handle_merchant_chat
        result = handle_merchant_chat(
            thread_id=request.thread_id,
            user_text=request.user_message,
            merchant_id=request.merchant_id
        )
        
        # Check for errors
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return ChatResponse(
            answer=result["answer"],
            status=result["status"],
            collected_data=result["collected_data"],
            next_field=result["next_field"]
        )

    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@router.get("/merchants/{merchant_id}/conversations")
async def get_merchant_conversations(merchant_id: int):
    """Get all conversations for a merchant."""
    
    from app.database import get_db_cursor
    
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT thread_id, collected_data, status, created_at, updated_at
                FROM conversation_sessions 
                WHERE merchant_id = %s
                ORDER BY updated_at DESC
            """, (merchant_id,))
            
            conversations = []
            for row in cursor.fetchall():
                conversations.append({
                    'thread_id': row[0],
                    'collected_data': json.loads(row[1]),
                    'status': row[2],
                    'created_at': row[3].isoformat(),
                    'updated_at': row[4].isoformat()
                })
            
            return conversations
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching conversations: {str(e)}")