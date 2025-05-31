from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams
from pipecat.services.gemini_multimodal_live.gemini import (
    GeminiMultimodalLiveLLMService,
)
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from loguru import logger
import os
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from supabase import AsyncClient
from supa.utils.supabase_helpers import fetch_and_format

from pipecat.processors.frameworks.rtvi import (
    RTVIServerMessageFrame,
)


OLDEST_CONVERSATION_DATETIME = datetime.now(timezone.utc) - timedelta(weeks=2)


async def show_preformatted_text(params: FunctionCallParams):
    logger.info(f"Showing preformatted text: {params.arguments['text']}")
    if params.arguments.get("clear_pre_text"):
        await params.llm.push_frame(
            RTVIServerMessageFrame(data={"clear-pre-text": True})
        )
    await params.llm.push_frame(
        RTVIServerMessageFrame(data={"display-pre-text": params.arguments["text"]})
    )
    await params.result_callback({"result": "success"})


show_preformatted_text_schema = FunctionSchema(
    name="show_preformatted_text",
    description="Show the user preformatted text. Call this function if the user asks you to show them a list of their tasks, priorities, or other information.",
    properties={
        "text": {
            "description": "The text to show the user.",
            "type": "string",
        },
        "clear_pre_text": {
            "description": "Clear any existing preformatted text before showing the new text.",
            "type": "boolean",
        },
    },
    required=["text"],
)


class GeminiLiveTodo:
    def __init__(
        self,
        supabase: AsyncClient,
        user_id: str,
        system_instruction_file,
        messages: Optional[List] = None,
    ):
        if messages is None:
            messages = []
        self._system_instruction_file = system_instruction_file
        self._messages = messages
        self._supabase = supabase
        self._user_id = user_id
        self._llm_service = None

    async def llm(self):
        if self._llm_service is None:
            self._llm_service = GeminiMultimodalLiveLLMService(
                api_key=os.getenv("GOOGLE_API_KEY"),
                model=os.getenv(
                    "CONVERSATION_MODEL",
                    "models/gemini-2.5-flash-preview-native-audio-dialog",
                ),
                system_instruction=await self.load_system_instruction(
                    self._system_instruction_file
                ),
                voice_id="Puck",  # Aoede, Charon, Fenrir, Kore, Puck
                tools=ToolsSchema(standard_tools=[show_preformatted_text_schema]),
            )
            self._llm_service.register_function(
                "show_preformatted_text", show_preformatted_text
            )
        return self._llm_service

    async def load_system_instruction(self, filename: str):
        with open(filename, "r") as f:
            core_instruction = f.read()

        recent_conversations = await fetch_and_format(
            self._supabase, self._user_id, oldest=OLDEST_CONVERSATION_DATETIME
        )
        system_instruction = f"""
The current date and time now is {datetime.now().astimezone().strftime("%A, %B %d, %Y, at %I:%M %p")}.

{core_instruction}

{recent_conversations}

--- END OF RECENT CONVERSATIONS ---

----

You are now ready to have a new conversation with the user.
"""
        return system_instruction
