# app/merchant_config.py
from typing import Dict, List, Optional, Any
from utils.parser_my_style_location import extract_location, extract_style
from utils.lead import extract_name, extract_phone
import re

class FieldType:
    TEXT = "text"
    PHONE = "phone" 
    EMAIL = "email"
    NAME = "name"
    LOCATION = "location"
    STYLE = "style"
    CHOICE = "choice"
    NUMBER = "number"

class MerchantFieldConfig:
    """Configuration for a single field that merchant wants to collect."""
    
    def __init__(self, field_id: str, field_type: str, label: str, 
                 question: str, required: bool = True, 
                 choices: Optional[List[str]] = None,
                 validation_pattern: Optional[str] = None,
                 extractor_function: Optional[str] = None):
        self.field_id = field_id
        self.field_type = field_type
        self.label = label
        self.question = question
        self.required = required
        self.choices = choices or []
        self.validation_pattern = validation_pattern
        self.extractor_function = extractor_function
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'field_id': self.field_id,
            'field_type': self.field_type,
            'label': self.label,
            'question': self.question,
            'required': self.required,
            'choices': self.choices,
            'validation_pattern': self.validation_pattern,
            'extractor_function': self.extractor_function
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MerchantFieldConfig':
        return cls(
            field_id=data['field_id'],
            field_type=data['field_type'],
            label=data['label'],
            question=data['question'],
            required=data.get('required', True),
            choices=data.get('choices', []),
            validation_pattern=data.get('validation_pattern'),
            extractor_function=data.get('extractor_function')
        )

class InformationExtractor:
    """Extract information from user messages based on field type."""
    
    @staticmethod
    def extract_value(text: str, field_config: MerchantFieldConfig) -> Optional[str]:
        """Extract value from text based on field configuration."""
        field_type = field_config.field_type
        
        if field_type == FieldType.NAME:
            return extract_name(text)
        elif field_type == FieldType.PHONE:
            return extract_phone(text)
        elif field_type == FieldType.LOCATION:
            return extract_location(text)
        elif field_type == FieldType.STYLE:
            style_result = extract_style(text)
            return text if style_result and style_result.get("theme") != "generic" else None
        elif field_type == FieldType.EMAIL:
            return InformationExtractor._extract_email(text)
        elif field_type == FieldType.CHOICE:
            return InformationExtractor._extract_choice(text, field_config.choices)
        elif field_type == FieldType.NUMBER:
            return InformationExtractor._extract_number(text)
        elif field_type == FieldType.TEXT:
            return text.strip() if text.strip() else None
        
        return None
    
    @staticmethod
    def _extract_email(text: str) -> Optional[str]:
        """Extract email from text."""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        return match.group() if match else None
    
    @staticmethod
    def _extract_choice(text: str, choices: List[str]) -> Optional[str]:
        """Extract choice from predefined options."""
        text_lower = text.lower()
        for choice in choices:
            if choice.lower() in text_lower:
                return choice
        return None
    
    @staticmethod
    def _extract_number(text: str) -> Optional[str]:
        """Extract number from text."""
        number_pattern = r'\b\d+(?:\.\d+)?\b'
        match = re.search(number_pattern, text)
        return match.group() if match else None

class ConversationFlow:
    """Manage conversation flow based on merchant configuration."""
    
    def __init__(self, merchant_config: Dict[str, Any]):
        self.merchant_config = merchant_config
        self.fields = [MerchantFieldConfig.from_dict(field) for field in merchant_config['fields_config']]
        self.required_fields = [field for field in self.fields if field.required]
    
    def get_next_question(self, collected_data: Dict[str, str], current_field_index: int = 0) -> Optional[Dict[str, Any]]:
        """Get the next question to ask based on collected data."""
        
        # Check if we have all required fields
        missing_required = []
        for field in self.required_fields:
            if field.field_id not in collected_data or not collected_data[field.field_id]:
                missing_required.append(field)
        
        if not missing_required:
            return None  # All required data collected
        
        # Return the first missing required field
        next_field = missing_required[0]
        return {
            'field': next_field.to_dict(),
            'question': next_field.question,
            'field_index': self.fields.index(next_field)
        }
    
    def process_user_message(self, message: str, collected_data: Dict[str, str]) -> Dict[str, Any]:
        """Process user message and extract relevant information."""
        extracted_values = {}
        
        # Try to extract values for all missing fields
        for field in self.fields:
            if field.field_id not in collected_data or not collected_data[field.field_id]:
                value = InformationExtractor.extract_value(message, field)
                if value:
                    extracted_values[field.field_id] = value
        
        return extracted_values
    
    def is_complete(self, collected_data: Dict[str, str]) -> bool:
        """Check if all required data has been collected."""
        for field in self.required_fields:
            if field.field_id not in collected_data or not collected_data[field.field_id]:
                return False
        return True
    
    def get_completion_message(self, collected_data: Dict[str, str]) -> str:
        """Generate completion message with collected data."""
        merchant_name = self.merchant_config['name']
        company = self.merchant_config['company']
        
        # Build summary of collected data
        summary_parts = []
        for field in self.fields:
            if field.field_id in collected_data and collected_data[field.field_id]:
                summary_parts.append(f"{field.label}: {collected_data[field.field_id]}")
        
        summary = ", ".join(summary_parts)
        
        return f"Perfect! Thank you. I have all the details I need - {summary}. {merchant_name} from {company} will follow up with you soon."

# Predefined merchant templates
MERCHANT_TEMPLATES = {
    "interior_design": [
        MerchantFieldConfig("name", FieldType.NAME, "Name", "May I have your name?"),
        MerchantFieldConfig("phone", FieldType.PHONE, "Phone", "What's your phone number?"),
        MerchantFieldConfig("location", FieldType.LOCATION, "Location", "What's the location of your property?"),
        MerchantFieldConfig("style", FieldType.STYLE, "Style Preference", "What kind of style or vibe do you want for your space?")
    ],
    "real_estate": [
        MerchantFieldConfig("name", FieldType.NAME, "Name", "May I have your name?"),
        MerchantFieldConfig("phone", FieldType.PHONE, "Phone", "What's your contact number?"),
        MerchantFieldConfig("email", FieldType.EMAIL, "Email", "What's your email address?"),
        MerchantFieldConfig("property_type", FieldType.CHOICE, "Property Type", 
                          "What type of property are you looking for?",
                          choices=["Apartment", "Condo", "House", "Townhouse", "Commercial"]),
        MerchantFieldConfig("budget", FieldType.NUMBER, "Budget", "What's your budget range?"),
        MerchantFieldConfig("location", FieldType.LOCATION, "Preferred Location", "Which area are you interested in?")
    ],
    "restaurant": [
        MerchantFieldConfig("name", FieldType.NAME, "Name", "May I have your name for the reservation?"),
        MerchantFieldConfig("phone", FieldType.PHONE, "Phone", "What's your contact number?"),
        MerchantFieldConfig("party_size", FieldType.NUMBER, "Party Size", "How many people will be dining?"),
        MerchantFieldConfig("date_time", FieldType.TEXT, "Date & Time", "When would you like to make the reservation?"),
        MerchantFieldConfig("dietary_restrictions", FieldType.TEXT, "Dietary Restrictions", 
                          "Do you have any dietary restrictions or special requests?", required=False)
    ],
    "fitness": [
        MerchantFieldConfig("name", FieldType.NAME, "Name", "What's your name?"),
        MerchantFieldConfig("phone", FieldType.PHONE, "Phone", "What's your phone number?"),
        MerchantFieldConfig("email", FieldType.EMAIL, "Email", "What's your email address?"),
        MerchantFieldConfig("fitness_goal", FieldType.CHOICE, "Fitness Goal", 
                          "What's your primary fitness goal?",
                          choices=["Weight Loss", "Muscle Gain", "General Fitness", "Athletic Performance"]),
        MerchantFieldConfig("experience", FieldType.CHOICE, "Experience Level", 
                          "What's your fitness experience level?",
                          choices=["Beginner", "Intermediate", "Advanced"])
    ]
}