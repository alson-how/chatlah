"""
Google Calendar integration for automated appointment scheduling.
Handles OAuth2 authentication, availability checking, and appointment creation.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from urllib.parse import urlencode

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']

# OAuth2 credentials - these will be provided by the user
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')

class GoogleCalendarManager:
    def __init__(self, user_credentials: Optional[str] = None):
        self.service = None
        self.calendar_id = 'primary'  # Use primary calendar
        self.user_credentials = user_credentials
        
    def get_auth_url(self, state: str = None) -> str:
        """Generate Google OAuth2 authorization URL for user to sign in."""
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            raise ValueError("Google OAuth credentials not configured")
            
        # Use the current domain from environment
        domain = os.getenv('REPLIT_DEV_DOMAIN', 'localhost:5000')
        redirect_uri = f'https://{domain}/api/appointments/oauth/callback'
        
        flow = Flow.from_client_config({
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        }, scopes=SCOPES)
        
        flow.redirect_uri = redirect_uri
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state
        )
        
        return auth_url
    
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens."""
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            raise ValueError("Google OAuth credentials not configured")
            
        domain = os.getenv('REPLIT_DEV_DOMAIN', 'localhost:5000')
        redirect_uri = f'https://{domain}/api/appointments/oauth/callback'
        
        flow = Flow.from_client_config({
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        }, scopes=SCOPES)
        
        flow.redirect_uri = redirect_uri
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        return {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
    
    def authenticate_with_tokens(self, token_data: Dict[str, Any]) -> bool:
        """Authenticate with stored user tokens."""
        try:
            credentials = Credentials(
                token=token_data['access_token'],
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes')
            )
            
            # Refresh token if expired
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            
            self.service = build('calendar', 'v3', credentials=credentials)
            return True
            
        except Exception as e:
            print(f"Calendar authentication failed: {e}")
            return False
            
        return False
    
    def get_available_slots(self, start_date: datetime = None, days_ahead: int = 14) -> List[Dict[str, Any]]:
        """Get available appointment slots within the next specified days."""
        if not self.service:
            return []
            
        if not start_date:
            start_date = datetime.now()
            
        # Define business hours (9 AM to 6 PM, Monday to Friday)
        business_start_hour = 9
        business_end_hour = 18
        
        available_slots = []
        
        try:
            for day_offset in range(days_ahead):
                current_date = start_date + timedelta(days=day_offset)
                
                # Skip weekends
                if current_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                    continue
                
                # Get events for this day
                day_start = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = current_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                events_result = self.service.events().list(
                    calendarId=self.calendar_id,
                    timeMin=day_start.isoformat() + 'Z',
                    timeMax=day_end.isoformat() + 'Z',
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                
                # Find available slots (2-hour blocks)
                for hour in range(business_start_hour, business_end_hour - 1, 2):
                    slot_start = current_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                    slot_end = slot_start + timedelta(hours=2)
                    
                    # Check if slot conflicts with existing events
                    is_available = True
                    for event in events:
                        event_start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date')))
                        event_end = datetime.fromisoformat(event['end'].get('dateTime', event['end'].get('date')))
                        
                        if (slot_start < event_end and slot_end > event_start):
                            is_available = False
                            break
                    
                    if is_available and slot_start > datetime.now():
                        available_slots.append({
                            'start_time': slot_start,
                            'end_time': slot_end,
                            'formatted_time': slot_start.strftime('%A, %B %d at %I:%M %p'),
                            'date': slot_start.strftime('%Y-%m-%d'),
                            'time': slot_start.strftime('%H:%M')
                        })
                        
        except HttpError as error:
            print(f'An error occurred: {error}')
            
        return available_slots[:10]  # Return first 10 available slots
    
    def create_appointment(self, 
                          client_name: str,
                          client_phone: str,
                          client_location: str,
                          style_preference: str,
                          appointment_datetime: datetime,
                          duration_hours: int = 2) -> Optional[Dict[str, Any]]:
        """Create a new appointment in Google Calendar."""
        if not self.service:
            return None
            
        try:
            # Calculate end time
            end_time = appointment_datetime + timedelta(hours=duration_hours)
            
            # Create event
            event = {
                'summary': f'Interior Design Consultation - {client_name}',
                'description': f'''
Interior Design Consultation

Client: {client_name}
Phone: {client_phone}
Location: {client_location}
Style Preference: {style_preference}

This is an automated booking from the Jablanc Interior chat system.
                '''.strip(),
                'start': {
                    'dateTime': appointment_datetime.isoformat(),
                    'timeZone': 'Asia/Kuala_Lumpur',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'Asia/Kuala_Lumpur',
                },
                'attendees': [
                    {'email': client_phone + '@placeholder.com', 'displayName': client_name},
                ],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 60},       # 1 hour before
                    ],
                },
            }
            
            # Insert the event
            created_event = self.service.events().insert(
                calendarId=self.calendar_id, 
                body=event
            ).execute()
            
            return {
                'event_id': created_event['id'],
                'event_link': created_event.get('htmlLink'),
                'start_time': appointment_datetime,
                'end_time': end_time,
                'summary': event['summary']
            }
            
        except HttpError as error:
            print(f'An error occurred creating appointment: {error}')
            return None

    def get_next_available_slot(self) -> Optional[Dict[str, Any]]:
        """Get the next available appointment slot."""
        available_slots = self.get_available_slots()
        return available_slots[0] if available_slots else None


def schedule_appointment_for_lead(name: str, phone: str, location: str, style: str, 
                                merchant_tokens: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Schedule an appointment for a lead with complete information.
    Returns appointment details or error message.
    """
    if not merchant_tokens:
        return {
            'success': False,
            'auth_required': True,
            'message': 'Calendar integration requires Google account connection.',
            'fallback_message': f"Hi {name}, thank you for providing all your details. We'll contact you at {phone} within 24 hours to schedule your consultation for your {style} project in {location}."
        }
    
    calendar_manager = GoogleCalendarManager()
    
    # Try to authenticate with merchant's tokens
    if not calendar_manager.authenticate_with_tokens(merchant_tokens):
        return {
            'success': False,
            'auth_required': True,
            'message': 'Calendar authentication expired. Please reconnect your Google account.',
            'fallback_message': f"Hi {name}, we'll contact you at {phone} within 24 hours to schedule your consultation."
        }
    
    # Get next available slot
    next_slot = calendar_manager.get_next_available_slot()
    
    if not next_slot:
        return {
            'success': False,
            'message': 'No available appointment slots found in the next 2 weeks.',
            'fallback_message': f"Hi {name}, our calendar is quite busy. We'll contact you at {phone} within 24 hours to find a suitable time for your consultation."
        }
    
    # Create the appointment
    appointment = calendar_manager.create_appointment(
        client_name=name,
        client_phone=phone,
        client_location=location,
        style_preference=style,
        appointment_datetime=next_slot['start_time']
    )
    
    if appointment:
        return {
            'success': True,
            'appointment': appointment,
            'message': f"Perfect! I've scheduled your consultation for {next_slot['formatted_time']}. You'll receive a calendar invitation and reminder. Looking forward to discussing your {style} project in {location}!",
            'details': {
                'date_time': next_slot['formatted_time'],
                'duration': '2 hours',
                'event_id': appointment['event_id']
            }
        }
    else:
        return {
            'success': False,
            'message': 'Unable to create calendar appointment automatically.',
            'fallback_message': f"Hi {name}, I have all your details. We'll contact you at {phone} within 24 hours to schedule your consultation."
        }


def get_available_appointment_slots(merchant_tokens: Dict[str, Any], days_ahead: int = 7) -> List[Dict[str, Any]]:
    """Get list of available appointment slots for user selection."""
    calendar_manager = GoogleCalendarManager()
    
    if not calendar_manager.authenticate_with_tokens(merchant_tokens):
        return []
    
    return calendar_manager.get_available_slots(days_ahead=days_ahead)