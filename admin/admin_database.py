# admin_database.py
import os
import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor
import json
from typing import List, Dict, Optional

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_admin_tables():
    """Initialize admin tables for custom field configuration."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Create admin_field_configs table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin_field_configs (
                    id SERIAL PRIMARY KEY,
                    field_name VARCHAR(100) NOT NULL UNIQUE,
                    field_label VARCHAR(200) NOT NULL,
                    field_type VARCHAR(50) NOT NULL DEFAULT 'text',
                    question_text TEXT NOT NULL,
                    is_required BOOLEAN DEFAULT true,
                    is_active BOOLEAN DEFAULT true,
                    sort_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create default fields if they don't exist
            default_fields = [
                ('name', 'Name', 'text', 'May I have your name?', True, True, 1),
                ('phone', 'Phone Number', 'phone', 'What\'s the best phone number to reach you?', True, True, 2),
                ('style', 'Design Style', 'text', 'What kind of style or vibe you want?', True, True, 3),
                ('location', 'Location', 'text', 'Which area is the property located?', True, True, 4),
                ('scope', 'Project Scope', 'textarea', 'Which spaces are in scope? For example, living, kitchen, master bedroom.', False, True, 5)
            ]
            
            for field_name, field_label, field_type, question_text, is_required, is_active, sort_order in default_fields:
                cur.execute("""
                    INSERT INTO admin_field_configs (field_name, field_label, field_type, question_text, is_required, is_active, sort_order)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (field_name) DO UPDATE SET
                        field_label = EXCLUDED.field_label,
                        field_type = EXCLUDED.field_type,
                        question_text = EXCLUDED.question_text,
                        is_required = EXCLUDED.is_required,
                        is_active = EXCLUDED.is_active,
                        sort_order = EXCLUDED.sort_order;
                """, (field_name, field_label, field_type, question_text, is_required, is_active, sort_order))
            
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_active_field_configs() -> List[Dict]:
    """Get all active field configurations."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM admin_field_configs 
                WHERE is_active = true 
                ORDER BY sort_order, field_name
            """)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def get_all_field_configs() -> List[Dict]:
    """Get all field configurations for admin interface."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM admin_field_configs 
                ORDER BY sort_order, field_name
            """)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def create_field_config(field_name: str, field_label: str, field_type: str, question_text: str, is_required: bool = False) -> Dict:
    """Create a new field configuration."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get next sort order
            cur.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 as next_order FROM admin_field_configs")
            order_result = cur.fetchone()
            next_order = order_result['next_order'] if order_result else 1
            
            # Check if field_name already exists
            cur.execute("SELECT COUNT(*) as field_count FROM admin_field_configs WHERE field_name = %s", (field_name,))
            count_result = cur.fetchone()
            count = count_result['field_count'] if count_result else 0
                
            if count > 0:
                raise ValueError(f"Field name '{field_name}' already exists. Please use a different name.")
            
            # Insert new field configuration  
            insert_query = """
                INSERT INTO admin_field_configs (field_name, field_label, field_type, question_text, is_required, is_active, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *;
            """
            insert_params = (field_name, field_label, field_type, question_text, is_required, True, next_order)
            
            cur.execute(insert_query, insert_params)
            row = cur.fetchone()
            
            if row is None:
                raise ValueError("Failed to create field configuration - no row returned")
            
            conn.commit()
            return dict(row)
    except psycopg2.Error as e:
        conn.rollback()
        print(f"PostgreSQL error in create_field_config: {e}")
        raise ValueError(f"Database error: {e}")
    except Exception as e:
        conn.rollback()
        print(f"General error in create_field_config: {e}")
        raise ValueError(f"Error creating field: {e}")
    finally:
        conn.close()

def update_field_config(field_id: int, **kwargs) -> Dict:
    """Update field configuration."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Build update query dynamically
            set_clauses = []
            values = []
            for key, value in kwargs.items():
                if key in ['field_label', 'field_type', 'question_text', 'is_required', 'is_active', 'sort_order']:
                    set_clauses.append(f"{key} = %s")
                    values.append(value)
            
            if not set_clauses:
                return {}
                
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(field_id)
            
            query = f"""
                UPDATE admin_field_configs 
                SET {', '.join(set_clauses)}
                WHERE id = %s
                RETURNING *;
            """
            
            cur.execute(query, values)
            result = dict(cur.fetchone())
            conn.commit()
            return result
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def delete_field_config(field_id: int) -> bool:
    """Delete field configuration."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM admin_field_configs WHERE id = %s", (field_id,))
            deleted = cur.rowcount > 0
            conn.commit()
            return deleted
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# Initialize tables on import
try:
    init_admin_tables()
except Exception as e:
    print(f"Warning: Could not initialize admin tables: {e}")