"""
Google Calendar integration for automated appointment scheduling.
Handles calendar authentication, availability checking, and appointment creation.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']

class GoogleCalendarManager:
    def __init__(self):
        self.service = None
        self.calendar_id = 'primary'  # Use primary calendar
        
    def authenticate(self) -> bool:
        """Authenticate with Google Calendar API using service account or OAuth."""
        try:
            # Try to load existing credentials
            creds = None
            
            # Check for service account key from environment
            service_account_info = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            if service_account_info:
                from google.oauth2 import service_account
                service_account_data = json.loads(service_account_info)
                creds = service_account.Credentials.from_service_account_info(
                    service_account_data, scopes=SCOPES
                )
            else:
                # Fallback to OAuth flow (requires user interaction)
                # In production, this should be pre-configured
                print("WARNING: No service account found. Calendar integration requires Google credentials.")
                return False
            
            if creds:
                self.service = build('calendar', 'v3', credentials=creds)
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


def schedule_appointment_for_lead(name: str, phone: str, location: str, style: str) -> Dict[str, Any]:
    """
    Schedule an appointment for a lead with complete information.
    Returns appointment details or error message.
    """
    calendar_manager = GoogleCalendarManager()
    
    # Try to authenticate
    if not calendar_manager.authenticate():
        return {
            'success': False,
            'message': 'Calendar service not available. Please contact us directly to schedule your appointment.',
            'fallback_message': f"Hi {name}, thank you for providing all your details. We'll contact you at {phone} within 24 hours to schedule your consultation for your {style} project in {location}."
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


def get_available_appointment_slots(days_ahead: int = 7) -> List[Dict[str, Any]]:
    """Get list of available appointment slots for user selection."""
    calendar_manager = GoogleCalendarManager()
    
    if not calendar_manager.authenticate():
        return []
    
    return calendar_manager.get_available_slots(days_ahead=days_ahead)