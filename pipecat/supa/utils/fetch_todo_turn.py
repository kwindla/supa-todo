#!/usr/bin/env python3
"""
Utility script to fetch todo_turns from Supabase using supabase-py.
Usage: fetch_todo_turn.py --user_id USER_ID [--conversation_id CONV_ID]
"""

import asyncio
import os
import sys
import argparse
import json
from supabase import acreate_client, AsyncClient
from supabase_helpers import fetch_conversation_turns, fetch_and_format
import dateparser
from datetime import datetime, timezone


async def main():
    parser = argparse.ArgumentParser(description="Fetch todo_turns from Supabase")
    parser.add_argument("--user_id", required=True, help="User ID")
    parser.add_argument("--conversation_id", help="Conversation ID (optional)")
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Number of conversations to fetch (default: 50)",
    )
    parser.add_argument(
        "--oldest",
        help="Fetch conversations newer than this date (human-readable, e.g. 'two days ago')",
    )
    args = parser.parse_args()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        print(
            "Please set SUPABASE_URL and SUPABASE_KEY environment variables",
            file=sys.stderr,
        )
        sys.exit(1)
    supabase: AsyncClient = await acreate_client(supabase_url, supabase_key)

    oldest = None
    if args.oldest:
        oldest_dt = dateparser.parse(args.oldest)
        if oldest_dt is None:
            print(f"Could not parse date '{args.oldest}'", file=sys.stderr)
            sys.exit(1)
        if oldest_dt.tzinfo is None:
            oldest_dt = oldest_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
        oldest = oldest_dt.astimezone(timezone.utc)
        print(f"Fetching conversations newer than {oldest}")

    if args.conversation_id:
        data = await fetch_conversation_turns(
            supabase, args.user_id, args.conversation_id
        )
        print(json.dumps(data, indent=2, default=str))
    else:
        data = await fetch_and_format(supabase, args.user_id, args.limit, oldest)
        print(data)


if __name__ == "__main__":
    asyncio.run(main())
