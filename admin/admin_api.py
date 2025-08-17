# admin_api.py
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
from admin.admin_database import (
    get_all_field_configs, get_active_field_configs, 
    create_field_config, update_field_config, delete_field_config
)

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")

class FieldConfigCreate(BaseModel):
    field_name: str
    field_label: str
    field_type: str = "text"
    question_text: str
    is_required: bool = False

class FieldConfigUpdate(BaseModel):
    field_label: Optional[str] = None
    field_type: Optional[str] = None
    question_text: Optional[str] = None
    is_required: Optional[bool] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin dashboard home page with website crawling interface."""
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})

@router.get("/admin/fields", response_class=HTMLResponse)
async def admin_fields_page(request: Request):
    """Admin page for managing chatbot information collection fields."""
    field_configs = get_all_field_configs()
    return templates.TemplateResponse("admin_fields.html", {
        "request": request, 
        "field_configs": field_configs
    })

@router.get("/admin/api/fields")
async def get_field_configs():
    """API endpoint to get all field configurations."""
    return {"field_configs": get_all_field_configs()}

@router.get("/admin/api/fields/active")
async def get_active_fields():
    """API endpoint to get active field configurations."""
    return {"field_configs": get_active_field_configs()}

@router.post("/admin/api/fields")
async def create_field(field_config: FieldConfigCreate):
    """API endpoint to create a new field configuration."""
    try:
        result = create_field_config(
            field_config.field_name,
            field_config.field_label,
            field_config.field_type,
            field_config.question_text,
            field_config.is_required
        )
        return {"success": True, "field_config": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/admin/api/fields/{field_id}")
async def update_field(field_id: int, field_config: FieldConfigUpdate):
    """API endpoint to update field configuration."""
    try:
        update_data = {k: v for k, v in field_config.dict().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        result = update_field_config(field_id, **update_data)
        if not result:
            raise HTTPException(status_code=404, detail="Field configuration not found")
        
        return {"success": True, "field_config": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/admin/api/fields/{field_id}")
async def delete_field(field_id: int):
    """API endpoint to delete field configuration."""
    try:
        success = delete_field_config(field_id)
        if not success:
            raise HTTPException(status_code=404, detail="Field configuration not found")
        
        return {"success": True, "message": "Field configuration deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/admin/api/fields/{field_id}/toggle")
async def toggle_field_active(field_id: int):
    """API endpoint to toggle field active status."""
    try:
        # Get current field config
        all_configs = get_all_field_configs()
        current_config = next((c for c in all_configs if c['id'] == field_id), None)
        
        if not current_config:
            raise HTTPException(status_code=404, detail="Field configuration not found")
        
        # Toggle active status
        new_active = not current_config['is_active']
        result = update_field_config(field_id, is_active=new_active)
        
        return {"success": True, "field_config": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))