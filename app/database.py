# app/database.py
import psycopg2
import os
from contextlib import contextmanager
from typing import Dict, List, Optional, Any
import json

def get_db_connection():
    """Get database connection using environment variables."""
    return psycopg2.connect(
        host=os.getenv('PGHOST'),
        port=os.getenv('PGPORT'),
        database=os.getenv('PGDATABASE'),
        user=os.getenv('PGUSER'),
        password=os.getenv('PGPASSWORD')
    )

@contextmanager
def get_db_cursor():
    """Context manager for database operations."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

def init_merchant_tables():
    """Initialize merchant configuration and consumer data tables."""
    with get_db_cursor() as cursor:
        # Merchants table - stores merchant configuration
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS merchants (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                company VARCHAR(255) NOT NULL,
                fields_config JSONB NOT NULL,
                conversation_tone TEXT DEFAULT 'professional',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Consumer data table - stores collected information
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consumer_data (
                id SERIAL PRIMARY KEY,
                merchant_id INTEGER REFERENCES merchants(id),
                thread_id VARCHAR(255) NOT NULL,
                collected_data JSONB NOT NULL,
                status VARCHAR(50) DEFAULT 'incomplete',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Conversation sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                thread_id VARCHAR(255) PRIMARY KEY,
                merchant_id INTEGER REFERENCES merchants(id),
                current_field INTEGER DEFAULT 0,
                collected_data JSONB DEFAULT '{}',
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Google tokens table for calendar integration
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS merchant_google_tokens (
                merchant_id VARCHAR(255) PRIMARY KEY,
                tokens JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)

def create_merchant(name: str, company: str, fields_config: List[Dict], tone: str = 'professional') -> int:
    """Create a new merchant with custom field configuration."""
    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO merchants (name, company, fields_config, conversation_tone)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (name, company, json.dumps(fields_config), tone))
        
        return cursor.fetchone()[0]

def get_merchant_config(merchant_id: int) -> Optional[Dict]:
    """Get merchant configuration by ID."""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT id, name, company, fields_config, conversation_tone
            FROM merchants WHERE id = %s
        """, (merchant_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'name': row[1],
                'company': row[2],
                'fields_config': row[3] if isinstance(row[3], list) else json.loads(row[3]),
                'tone': row[4]
            }
        return None

def save_consumer_data(merchant_id: int, thread_id: str, data: Dict, status: str = 'incomplete'):
    """Save or update consumer data."""
    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO consumer_data (merchant_id, thread_id, collected_data, status)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (thread_id) DO UPDATE SET
                collected_data = EXCLUDED.collected_data,
                status = EXCLUDED.status,
                updated_at = NOW()
        """, (merchant_id, thread_id, json.dumps(data), status))

def get_conversation_session(thread_id: str) -> Optional[Dict]:
    """Get conversation session data."""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT thread_id, merchant_id, current_field, collected_data, status
            FROM conversation_sessions WHERE thread_id = %s
        """, (thread_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'thread_id': row[0],
                'merchant_id': row[1],
                'current_field': row[2],
                'collected_data': row[3] if isinstance(row[3], dict) else json.loads(row[3]),
                'status': row[4]
            }
        return None

def update_conversation_session(thread_id: str, merchant_id: int, current_field: int, 
                              collected_data: Dict, status: str = 'active'):
    """Update conversation session."""
    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO conversation_sessions (thread_id, merchant_id, current_field, collected_data, status)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (thread_id) DO UPDATE SET
                current_field = EXCLUDED.current_field,
                collected_data = EXCLUDED.collected_data,
                status = EXCLUDED.status,
                updated_at = NOW()
        """, (thread_id, merchant_id, current_field, json.dumps(collected_data), status))

def save_conversation_session(thread_id: str, merchant_id: int, current_field: int, collected_data: Dict, status: str):
    """Save or update conversation session."""
    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO conversation_sessions (thread_id, merchant_id, current_field, collected_data, status)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (thread_id) DO UPDATE SET
                merchant_id = EXCLUDED.merchant_id,
                current_field = EXCLUDED.current_field,
                collected_data = EXCLUDED.collected_data,
                status = EXCLUDED.status,
                updated_at = NOW()
        """, (thread_id, merchant_id, current_field, json.dumps(collected_data), status))

# Legacy functions for backward compatibility
def save_lead(name: str, phone: str, thread_id: str, location: str = "", style_preference: str = ""):
    """Legacy function for backward compatibility."""
    # Default to Jablanc Interior (merchant_id = 1) if not specified
    data = {
        'name': name,
        'phone': phone,
        'location': location,
        'style_preference': style_preference
    }
    save_consumer_data(1, thread_id, data, 'complete')

def save_merchant_google_tokens(merchant_id: str, tokens: dict):
    """Save Google OAuth tokens for a merchant."""
    from datetime import datetime
    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO merchant_google_tokens (merchant_id, tokens, created_at, updated_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (merchant_id) 
            DO UPDATE SET tokens = %s, updated_at = %s
        """, (
            merchant_id, 
            json.dumps(tokens), 
            datetime.now(), 
            datetime.now(),
            json.dumps(tokens), 
            datetime.now()
        ))
        print(f"✅ SAVED GOOGLE TOKENS for merchant: {merchant_id}")

def get_merchant_google_tokens(merchant_id: str) -> Optional[dict]:
    """Get Google OAuth tokens for a merchant."""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT tokens FROM merchant_google_tokens WHERE merchant_id = %s", (merchant_id,))
        result = cursor.fetchone()
        if result:
            return json.loads(result[0])
        return None

def delete_merchant_google_tokens(merchant_id: str):
    """Delete Google OAuth tokens for a merchant."""
    with get_db_cursor() as cursor:
        cursor.execute("DELETE FROM merchant_google_tokens WHERE merchant_id = %s", (merchant_id,))
        print(f"✅ DELETED GOOGLE TOKENS for merchant: {merchant_id}")

def get_lead(thread_id: str) -> Optional[Dict]:
    """Legacy function for backward compatibility."""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT collected_data FROM consumer_data 
            WHERE thread_id = %s ORDER BY created_at DESC LIMIT 1
        """, (thread_id,))
        row = cursor.fetchone()
        if row:
            return row[0] if isinstance(row[0], dict) else json.loads(row[0])
        return None

def get_all_leads() -> List[Dict]:
    """Legacy function for backward compatibility."""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT thread_id, collected_data, created_at 
            FROM consumer_data ORDER BY created_at DESC
        """)
        leads = []
        for row in cursor.fetchall():
            data = row[1] if isinstance(row[1], dict) else json.loads(row[1])
            data['thread_id'] = row[0]
            data['created_at'] = row[2].isoformat()
            leads.append(data)
        return leads

# Initialize tables on import
try:
    init_merchant_tables()
    # Create default Jablanc Interior merchant if not exists
    with get_db_cursor() as cursor:
        cursor.execute("SELECT id FROM merchants WHERE company = 'Jablanc Interior' LIMIT 1")
        if not cursor.fetchone():
            from app.merchant_config import MERCHANT_TEMPLATES
            fields_config = [field.to_dict() for field in MERCHANT_TEMPLATES['interior_design']]
            create_merchant("Mei Yee", "Jablanc Interior", fields_config, "professional")
except Exception as e:
    print(f"Error initializing merchant tables: {e}")