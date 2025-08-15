# app/mcp_tools.py
from fastapi import APIRouter
from typing import List, Dict, Any
from .retriever import search as rag_search_impl
# from .crm import create_lead, update_lead
# from .calendar import find_slots, book_meeting
# from .quote import generate_quote
# from .payments import send_payment_link

router = APIRouter(prefix="/mcp")


@router.post("/rag_search")
def rag_search(payload: Dict[str, Any]):
    q = payload["query"]
    k = payload.get("k", 6)
    hits = rag_search_impl(q, top_k=k)
    # return lean context for the model
    return [{
        "text": h["text"],
        "url": h["meta"]["url"],
        "title": h["meta"]["title"]
    } for h in hits]


# @router.post("/crm_create_lead")
# def crm_create(payload: Dict[str, Any]):
#     return create_lead(payload)


# @router.post("/crm_update_lead") 
# def crm_update(payload: Dict[str, Any]):
#     return update_lead(payload["lead_id"], payload["fields"])


@router.post("/calendar_find_slots")
def cal_find(payload: Dict[str, Any]):
    return find_slots(payload)


@router.post("/calendar_book_meeting")
def cal_book(payload: Dict[str, Any]):
    return book_meeting(payload)


@router.post("/quote_generate")
def quote_gen(payload: Dict[str, Any]):
    return generate_quote(payload)


@router.post("/payments_send_link")
def pay_link(payload: Dict[str, Any]):
    return send_payment_link(payload)
