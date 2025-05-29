#!/usr/bin/env python3
"""
Utility script to insert a single todo_turn into the todo_turns table using supabase-py.
Usage: insert_todo_turn.py --user_id USER_ID --conversation_id CONV_ID --role ROLE --content CONTENT
"""
import os
import sys
import argparse
from datetime import datetime, timezone
from supabase import create_client, Client

def main():
    parser = argparse.ArgumentParser(description="Insert a todo_turn into Supabase")
    parser.add_argument("--user_id", required=True, help="User ID")
    parser.add_argument("--conversation_id", required=True, help="Conversation ID")
    parser.add_argument("--role", required=True, help="Role (e.g. user, assistant)")
    parser.add_argument("--content", required=True, help="Content of the message")
    args = parser.parse_args()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        print("Please set SUPABASE_URL and SUPABASE_KEY environment variables", file=sys.stderr)
        sys.exit(1)
    supabase: Client = create_client(supabase_url, supabase_key)

    # use current UTC timestamp
    timestamp = datetime.now(timezone.utc).isoformat()
    record = {
        "timestamp": timestamp,
        "user_id": args.user_id,
        "conversation_id": args.conversation_id,
        "role": args.role,
        "content": args.content,
    }

    response = supabase.from_("todo_turns").insert(record).execute()
    if hasattr(response, "error") and response.error:
        print(f"Error inserting todo_turn: {response.error}", file=sys.stderr)
        sys.exit(1)
    # older versions may return a dict
    data = getattr(response, "data", None) or response.get("data")
    print("Inserted todo_turn:", data)

if __name__ == "__main__":
    main()
