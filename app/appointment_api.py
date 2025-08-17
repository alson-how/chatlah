"""
API endpoints for appointment management and Google OAuth calendar integration.
"""

from fastapi import APIRouter, HTTPException, Request, Query, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.calendar_integration import GoogleCalendarManager
from app.database import save_merchant_google_tokens, get_merchant_google_tokens
import os

router = APIRouter()

class AuthRequest(BaseModel):
    merchant_id: Optional[str] = "default"
    redirect_url: Optional[str] = None

class AppointmentRequest(BaseModel):
    name: str
    phone: str
    location: str
    style_preference: str
    merchant_id: str = "default"
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
    auth_required: Optional[bool] = False

@router.get("/oauth/signin")
async def google_signin(merchant_id: str = "default", redirect_url: str = None):
    """Initiate Google OAuth2 flow for calendar access."""
    try:
        calendar_manager = GoogleCalendarManager()
        auth_url = calendar_manager.get_auth_url(state=f"{merchant_id}|{redirect_url or ''}")
        
        return {
            "auth_url": auth_url,
            "message": "Please visit the auth_url to connect your Google Calendar"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate auth URL: {str(e)}")

@router.get("/oauth/callback")
async def google_oauth_callback(code: str = Query(...), state: str = Query(None)):
    """Handle Google OAuth2 callback and save tokens."""
    try:
        # Parse state to get merchant_id and redirect_url
        merchant_id = "default"
        redirect_url = None
        if state:
            parts = state.split("|", 1)
            merchant_id = parts[0]
            redirect_url = parts[1] if len(parts) > 1 and parts[1] else None
        
        calendar_manager = GoogleCalendarManager()
        tokens = calendar_manager.exchange_code_for_tokens(code)
        
        # Save tokens to database
        save_merchant_google_tokens(merchant_id, tokens)
        
        # Redirect to success page or specified URL
        if redirect_url:
            return RedirectResponse(url=redirect_url)
        
        return HTMLResponse(content="""
        <html>
            <head><title>Calendar Connected</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h2 style="color: #4CAF50;">✅ Google Calendar Connected Successfully!</h2>
                <p>Your calendar is now integrated and appointments will be automatically scheduled.</p>
                <p>You can close this window and return to your dashboard.</p>
                <script>
                    setTimeout(() => {
                        window.close();
                    }, 3000);
                </script>
            </body>
        </html>
        """)
        
    except Exception as e:
        return HTMLResponse(content=f"""
        <html>
            <head><title>Connection Failed</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h2 style="color: #f44336;">❌ Calendar Connection Failed</h2>
                <p>Error: {str(e)}</p>
                <p>Please try again or contact support.</p>
            </body>
        </html>
        """, status_code=400)

@router.get("/available-slots")
async def get_available_slots(merchant_id: str = "default", days_ahead: int = 7):
    """Get list of available appointment slots."""
    try:
        tokens = get_merchant_google_tokens(merchant_id)
        if not tokens:
            raise HTTPException(status_code=401, detail="Calendar not connected. Please authenticate first.")
        
        from app.calendar_integration import get_available_appointment_slots
        slots = get_available_appointment_slots(tokens, days_ahead=days_ahead)
        
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get available slots: {str(e)}")

@router.post("/schedule", response_model=AppointmentResponse)
async def schedule_appointment(request: AppointmentRequest):
    """Schedule a new appointment."""
    try:
        tokens = get_merchant_google_tokens(request.merchant_id)
        
        from app.calendar_integration import schedule_appointment_for_lead
        result = schedule_appointment_for_lead(
            name=request.name,
            phone=request.phone,
            location=request.location,
            style=request.style_preference,
            merchant_tokens=tokens
        )
        
        return AppointmentResponse(
            success=result['success'],
            message=result['message'],
            appointment_id=result.get('details', {}).get('event_id'),
            details=result.get('details'),
            auth_required=result.get('auth_required', False)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule appointment: {str(e)}")

@router.get("/calendar-status")
async def get_calendar_status(merchant_id: str = "default"):
    """Check if Google Calendar integration is working."""
    tokens = get_merchant_google_tokens(merchant_id)
    
    if not tokens:
        return {
            "calendar_integration_active": False,
            "message": "Calendar not connected. Please authenticate with Google.",
            "auth_required": True
        }
    
    # Test authentication
    calendar_manager = GoogleCalendarManager()
    is_authenticated = calendar_manager.authenticate_with_tokens(tokens)
    
    return {
        "calendar_integration_active": is_authenticated,
        "message": "Calendar integration is working" if is_authenticated else "Calendar authentication expired",
        "auth_required": not is_authenticated
    }

@router.delete("/disconnect")
async def disconnect_calendar(merchant_id: str = "default"):
    """Disconnect Google Calendar integration."""
    try:
        from app.database import delete_merchant_google_tokens
        delete_merchant_google_tokens(merchant_id)
        
        return {
            "success": True,
            "message": "Calendar disconnected successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect calendar: {str(e)}")