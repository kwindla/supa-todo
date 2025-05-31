#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import asyncio
import sys
import argparse
import os
from datetime import datetime, timezone, timedelta
from typing import List, Any
import json

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    TranscriptionMessage,
    TranscriptionUpdateFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.transcript_processor import TranscriptProcessor

from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecatcloud.agent import (
    DailySessionArguments,
    SessionArguments,
)
from supabase import acreate_client, AsyncClient


from pipecat.processors.frameworks.rtvi import (
    RTVIConfig,
    RTVIObserver,
    RTVIProcessor,
    RTVIServerMessageFrame,
)

from gemini_live import GeminiLiveTodo

load_dotenv(override=True)

logger.remove()
logger.add(sys.stderr, level="DEBUG")

OLDEST_CONVERSATION_DATETIME = datetime.now(timezone.utc) - timedelta(weeks=2)

CONVERSATION_MODEL = os.getenv(
    "CONVERSATION_MODEL", "models/gemini-2.5-flash-preview-native-audio-dialog"
)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

OLDEST_CONVERSATION_DATETIME = datetime.now(timezone.utc) - timedelta(weeks=2)

DAILY_ROOM_URL = os.getenv("DAILY_ROOM_URL")
DAILY_TOKEN = os.getenv("DAILY_TOKEN")


class TranscriptHandler:
    """Handles real-time transcript processing and output."""

    def __init__(self, supabase: AsyncClient, user_id: str):
        """Initialize handler."""
        self.messages: List[TranscriptionMessage] = []

        self._user_id = user_id
        # _conversation_id should be a user-readable timestamp with 1s granularity
        self._conversation_id = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        self._supabase: AsyncClient = supabase
        logger.debug("TranscriptHandler initialized")

    async def save_message(self, message: TranscriptionMessage):
        """Save a single transcript message.

        Args:
            message: The message to save
        """

        # use current UTC timestamp
        timestamp = datetime.now(timezone.utc).isoformat()
        record = {
            "timestamp": timestamp,
            "user_id": self._user_id,
            "conversation_id": self._conversation_id,
            "role": message.role,
            "content": message.content,
        }

        response = await self._supabase.from_("todo_turns").insert(record).execute()
        if hasattr(response, "error") and response.error:
            logger.error(f"Error inserting todo_turn: {response.error}")

        timestamp = f"[{message.timestamp}] " if message.timestamp else ""
        line = f"{timestamp}{message.role}: {message.content}"
        # Always log the message
        logger.info(f"Transcript: {line}")

    async def on_transcript_update(
        self, processor: TranscriptProcessor, frame: TranscriptionUpdateFrame
    ):
        """Handle new transcript messages.

        Args:
            processor: The TranscriptProcessor that emitted the update
            frame: TranscriptionUpdateFrame containing new messages
        """
        logger.debug(
            f"Received transcript update with {len(frame.messages)} new messages"
        )

        for msg in frame.messages:
            self.messages.append(msg)
            await self.save_message(msg)


async def main(args: SessionArguments):
    logger.info(f"Starting bot")

    if isinstance(args, DailySessionArguments):
        logger.info(f"Starting Daily session with args body: {args.body}")
    else:
        logger.error("Invalid session arguments")
        return

    if args.body:
        user_id = args.body.get("user_id", os.getenv("USER_ID", "generic_user"))
    else:
        user_id = os.getenv("USER_ID", "generic_user")

    logger.debug(f"Creating Supabase client")
    supabase: AsyncClient = await acreate_client(SUPABASE_URL, SUPABASE_KEY)

    transport = DailyTransport(
        bot_name="todo helper",
        room_url=args.room_url,
        token=args.token,
        params=DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    # todo: move this inside GeminiLiveTodo?
    messages = [
        {
            "role": "user",
            "content": 'Please say the exact phrase "I am ready". Say it now.',
        }
    ]
    gemini_live_todo = GeminiLiveTodo(
        supabase,
        user_id,
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), "system-instruction.txt")
        ),
        messages=messages,
    )
    llm = await gemini_live_todo.llm()

    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    # Create transcript processor and handler
    transcript = TranscriptProcessor()
    transcript_handler = TranscriptHandler(supabase, user_id)

    pipeline = Pipeline(
        [
            transport.input(),  # Transport user input
            rtvi,
            context_aggregator.user(),  # User responses
            transcript.user(),  # User transcripts
            llm,  # LLM
            transport.output(),  # Transport bot output
            transcript.assistant(),  # Assistant transcripts
            context_aggregator.assistant(),  # Assistant spoken responses
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(allow_interruptions=True),
        observers=[RTVIObserver(rtvi)],
    )

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        logger.info("Pipecat client ready")
        await rtvi.set_bot_ready()
        await task.queue_frames([context_aggregator.user().get_context_frame()])
        logger.info("Sending server message frame")
        await task.queue_frames(
            [RTVIServerMessageFrame(data={"arbitrary_key": "arbitrary_value_23"})]
        )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")

    # Register event handler for transcript updates
    @transcript.event_handler("on_transcript_update")
    async def on_transcript_update(processor, frame):
        await transcript_handler.on_transcript_update(processor, frame)

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected")
        await task.cancel()

    @transport.event_handler("on_client_closed")
    async def on_client_closed(transport, client):
        logger.info(f"Client closed connection")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)


async def bot(args: SessionArguments):
    try:
        await main(args)
        logger.info("Bot process completed")
    except Exception as e:
        logger.exception(f"Error in bot process: {str(e)}")
        raise


async def local_dev_runner(body: Any):
    await bot(
        DailySessionArguments(
            room_url=DAILY_ROOM_URL,
            token=DAILY_TOKEN,
            session_id="local-dev",
            body=body,
        )
    )


if __name__ == "__main__":
    body_json = None
    if len(sys.argv) > 1:
        print(f"parsing json: {sys.argv[1]}")
        body_json = json.loads(sys.argv[1])
    asyncio.run(local_dev_runner(body_json))
