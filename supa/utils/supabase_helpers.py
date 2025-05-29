import sys
from supabase import AsyncClient
from datetime import datetime
from babel.dates import format_datetime
from typing import Optional


async def fetch_conversation_turns(
    client: AsyncClient, user_id: str, conversation_id: str
):
    query = client.from_("todo_turns").select("*")
    query = query.eq("user_id", user_id)
    query = query.eq("conversation_id", conversation_id)
    query = query.order("timestamp", desc=False)

    response = await query.execute()
    if hasattr(response, "error") and response.error:
        print(f"Error fetching todo_turns: {response.error}", file=sys.stderr)
        sys.exit(1)

    data = getattr(response, "data", None) or response.get("data")
    return data


async def fetch_and_format(
    client: AsyncClient,
    user_id: str,
    limit: Optional[int] = None,
    oldest: Optional[datetime] = None,
):
    text_block = ""

    query = client.from_("conversations").select("*")
    query = query.eq("user_id", user_id)
    query = query.order("last_ts", desc=True)
    if limit:
        query = query.limit(limit)
    if oldest:
        query = query.gte("last_ts", oldest)

    response = await query.execute()
    if hasattr(response, "error") and response.error:
        print(f"Error fetching conversations: {response.error}", file=sys.stderr)
        sys.exit(1)

    data = getattr(response, "data", "")
    data = data[::-1]
    for conversation in data:
        conversation_id = conversation["conversation_id"]
        turns = await fetch_conversation_turns(client, user_id, conversation_id)

        dt = datetime.fromisoformat(turns[0]["timestamp"].replace("Z", "+00:00"))
        dt = dt.astimezone()
        conversation_start_human = format_datetime(
            dt, "EEEE MMMM d, yyyy hh:mm:ss", locale="en_US"
        )
        text_block += f"---- Conversation: {conversation_start_human} ---\n\n"

        for turn in turns:
            text_block += f"{turn['role']}: {turn['content']}\n\n"
        text_block += "\n"

    return text_block
