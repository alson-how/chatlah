"""
API endpoints for appointment management and calendar integration.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.calendar_integration import (
    get_available_appointment_slots, 
    schedule_appointment_for_lead,
    GoogleCalendarManager
)

router = APIRouter()

class AppointmentRequest(BaseModel):
    name: str
    phone: str
    location: str
    style_preference: str
    preferred_datetime: Optional[str] = None

class AppointmentSlot(BaseModel):
    start_time: str
    end_time: str
    formatted_time: str
    date: str
    time: str

class AppointmentResponse(BaseModel):
    success: bool
    message: str
    appointment_id: Optional[str] = None
    details: Optional[dict] = None

@router.get("/available-slots", response_model=List[AppointmentSlot])
async def get_available_slots(days_ahead: int = 7):
    """Get list of available appointment slots."""
    try:
        slots = get_available_appointment_slots(days_ahead=days_ahead)
        return [
            AppointmentSlot(
                start_time=slot['start_time'].isoformat(),
                end_time=slot['end_time'].isoformat(),
                formatted_time=slot['formatted_time'],
                date=slot['date'],
                time=slot['time']
            )
            for slot in slots
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get available slots: {str(e)}")

@router.post("/schedule", response_model=AppointmentResponse)
async def schedule_appointment(request: AppointmentRequest):
    """Schedule a new appointment."""
    try:
        result = schedule_appointment_for_lead(
            name=request.name,
            phone=request.phone,
            location=request.location,
            style=request.style_preference
        )
        
        return AppointmentResponse(
            success=result['success'],
            message=result['message'],
            appointment_id=result.get('details', {}).get('event_id'),
            details=result.get('details')
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule appointment: {str(e)}")

@router.get("/calendar-status")
async def get_calendar_status():
    """Check if Google Calendar integration is working."""
    calendar_manager = GoogleCalendarManager()
    is_authenticated = calendar_manager.authenticate()
    
    return {
        "calendar_integration_active": is_authenticated,
        "message": "Calendar integration is working" if is_authenticated else "Calendar integration requires Google credentials"
    }

@router.post("/test-appointment")
async def test_appointment_creation():
    """Test endpoint for appointment creation (development only)."""
    test_result = schedule_appointment_for_lead(
        name="Test User",
        phone="0123456789",
        location="Test Location",
        style="Modern Test Style"
    )
    
    return {
        "test_result": test_result,
        "timestamp": datetime.now().isoformat()
    }