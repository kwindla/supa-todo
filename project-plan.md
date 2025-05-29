# Project plan for a voice AI todo list application.

Project components
  - Supabase backend
    - Tables
      - todo_turns
  - Pipecat bot
    - deploy to Pipecat Cloud

All code in Python. Dependencies in ./venv

## Supabase

### Environment

SUPABASE_DB_URL=postgres://postgres:<DB_PASSWORD>@yibowucndlvgbuqexwby.supabase.co:5432/postgres

### Tables

table: todo_turns - holds conversation messages across all conversations

    timestamp
    user_id
    conversation_id
    role
    content

view: conversations

Created using this SQL in the Supabase dashboard SQL Editor UI

```
CREATE VIEW conversations AS
  SELECT
    user_id,
    conversation_id,
    MAX(timestamp) AS last_ts
  FROM todo_turns
  GROUP BY conversation_id, user_id;
  ```

### Utility scripts and modules for Supabase in supa/utils

create_todo_turns_table.py

  - creates the todo_turns table
  - enables row-level security
  - creates a policy for authenticated users

insert_todo_turn.py

  - inserts a single turn into the todo_turns table
  - takes "user_id", "conversation_id", "role", and "content" command line arguments

fetch_todo_turn.py

  - fetches all turns from the todo_turns table
  - takes "user_id" and optional "conversation_id" command line arguments

supabase_helpers.py

  - utility functions for Supabase that scripts and bots can import

## Pipecat bot

Voice AI bot with a transcription processor that writes all turns to Supabase

Similar to [examples/foundation/28-transcription-processor.py](https://github.com/pipecat-ai/pipecat/blob/main/examples/foundational/28-transcription-processor.py)

