# app/database.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

DATABASE_URL = os.environ.get("DATABASE_URL")

@contextmanager
def get_db_connection():
    """Get database connection with context manager."""
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def save_lead(name: str, phone: str, thread_id: str, first_message: str = "", theme_interest: str = "", location: str = "", style_preference: str = ""):
    """Save or update lead information in the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Insert or update lead information
        cursor.execute("""
            INSERT INTO leads (name, phone, thread_id, first_message, theme_interest, location, style_preference, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (thread_id) 
            DO UPDATE SET 
                name = EXCLUDED.name,
                phone = EXCLUDED.phone,
                first_message = CASE 
                    WHEN leads.first_message = '' THEN EXCLUDED.first_message 
                    ELSE leads.first_message 
                END,
                theme_interest = CASE 
                    WHEN EXCLUDED.theme_interest != '' THEN EXCLUDED.theme_interest 
                    ELSE leads.theme_interest 
                END,
                location = CASE 
                    WHEN EXCLUDED.location != '' THEN EXCLUDED.location 
                    ELSE leads.location 
                END,
                style_preference = CASE 
                    WHEN EXCLUDED.style_preference != '' THEN EXCLUDED.style_preference 
                    ELSE leads.style_preference 
                END,
                updated_at = CURRENT_TIMESTAMP
        """, (name, phone, thread_id, first_message, theme_interest, location, style_preference))
        
        conn.commit()
        return cursor.rowcount

def get_lead(thread_id: str):
    """Get lead information by thread_id."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM leads WHERE thread_id = %s
        """, (thread_id,))
        
        return cursor.fetchone()

def get_all_leads():
    """Get all leads from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM leads ORDER BY created_at DESC
        """)
        
        return cursor.fetchall()