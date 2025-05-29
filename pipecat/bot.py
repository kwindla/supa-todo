#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import argparse
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import List

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    TranscriptionMessage,
    TranscriptionUpdateFrame,
    LLMMessagesAppendFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.transcript_processor import TranscriptProcessor
from pipecat.services.gemini_multimodal_live.gemini import (
    GeminiMultimodalLiveLLMService,
)
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.network.small_webrtc import SmallWebRTCTransport
from pipecat.transports.network.webrtc_connection import SmallWebRTCConnection
from supabase import acreate_client, AsyncClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from supa.utils.supabase_helpers import fetch_and_format

from pipecat.processors.frameworks.rtvi import (
    RTVIConfig,
    RTVIProcessor,
)

load_dotenv(override=True)


OLDEST_CONVERSATION_DATETIME = datetime.now(timezone.utc) - timedelta(weeks=2)

USER_ID = os.getenv("USER_ID", "kwindla")
CONVERSATION_MODEL = os.getenv(
    "CONVERSATION_MODEL", "models/gemini-2.5-flash-preview-native-audio-dialog"
)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


async def load_system_instruction(supabase: AsyncClient, filename: str):
    with open(filename, "r") as f:
        core_instruction = f.read()

    recent_conversations = await fetch_and_format(
        supabase, USER_ID, oldest=OLDEST_CONVERSATION_DATETIME
    )
    system_instruction = f"""
The current date and time now is {datetime.now().astimezone().strftime("%A, %B %d, %Y, at %I:%M %p")}.

{core_instruction}
    
{recent_conversations}

--- END OF RECENT CONVERSATIONS ---

You are now ready to have a new conversation with the user.
    """

    return system_instruction


class TranscriptHandler:
    """Handles real-time transcript processing and output."""

    def __init__(self, supabase: AsyncClient):
        """Initialize handler."""
        self.messages: List[TranscriptionMessage] = []

        self._user_id = USER_ID
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


async def run_bot(webrtc_connection: SmallWebRTCConnection, _: argparse.Namespace):
    logger.info(f"Starting bot")

    logger.debug(f"Creating Supabase client")
    supabase: AsyncClient = await acreate_client(SUPABASE_URL, SUPABASE_KEY)

    logger.debug("Loading system instruction")
    system_instruction = await load_system_instruction(
        supabase,
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), "system-instruction.txt")
        ),
    )

    transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    llm = GeminiMultimodalLiveLLMService(
        api_key=os.getenv("GOOGLE_API_KEY"),
        model=CONVERSATION_MODEL,
        system_instruction=system_instruction,
        voice_id="Puck",  # Aoede, Charon, Fenrir, Kore, Puck
    )

    messages = [
        {
            "role": "user",
            "content": 'Please say the exact phrase "I am ready". Say it now.',
        }
    ]

    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    # Create transcript processor and handler
    transcript = TranscriptProcessor()
    transcript_handler = TranscriptHandler(supabase)

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
    )

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        logger.info("Pipecat client ready")
        await rtvi.set_bot_ready()
        await task.queue_frames([context_aggregator.user().get_context_frame()])

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

    @transport.event_handler("on_client_closed")
    async def on_client_closed(transport, client):
        logger.info(f"Client closed connection")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)


if __name__ == "__main__":
    from run import main

    main()
