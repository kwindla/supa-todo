#!/usr/bin/env python3
"""
Utility script to create the todo_turns table in Supabase.
Prompts for Supabase database URL.
"""

import os
import sys
import psycopg2
import logging

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logging.info("Starting create_todo_turns_table script")
    # Prompt for Supabase database URL
    db_url = os.getenv("SUPABASE_DB_URL") or input("Enter your Supabase database URL (postgres://...): ")
    logging.info(f"Using SUPABASE_DB_URL: {db_url}")
    try:
        logging.info("Attempting to connect to database")
        conn = psycopg2.connect(db_url)
        logging.info("Database connection established")
    except Exception as e:
        logging.error(f"Error connecting to database: {e}", exc_info=True)
        sys.exit(1)
    cur = conn.cursor()
    logging.info("Database cursor created")
    create_table_query = """
    CREATE TABLE IF NOT EXISTS todo_turns (
        timestamp timestamptz NOT NULL,
        user_id text NOT NULL,
        conversation_id text NOT NULL,
        role text NOT NULL,
        content text NOT NULL
    );
    """
    try:
        logging.info("Executing CREATE TABLE query")
        cur.execute(create_table_query)
        conn.commit()
        logging.info("todo_turns table created (if not existed)")
        # Enable row-level security and policy
        logging.info("Enabling row-level security")
        cur.execute("ALTER TABLE IF EXISTS todo_turns ENABLE ROW LEVEL SECURITY;")
        logging.info("Creating RLS policy for authenticated users")
        # Drop and recreate policy to avoid unsupported IF NOT EXISTS syntax
        cur.execute("DROP POLICY IF EXISTS allow_authenticated ON todo_turns;")
        cur.execute("CREATE POLICY allow_authenticated ON todo_turns FOR ALL TO authenticated USING (true);")
        conn.commit()
        logging.info("RLS enabled and policy applied")
    except Exception as e:
        logging.error(f"Error creating table: {e}", exc_info=True)
        conn.rollback()
        sys.exit(1)
    finally:
        logging.info("Closing cursor and database connection")
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
