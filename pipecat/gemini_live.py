from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams
from pipecat.services.gemini_multimodal_live.gemini import (
    GeminiMultimodalLiveLLMService,
)
from pipecat.adapters.schemas.tools_schema import AdapterType, ToolsSchema
from loguru import logger
import os
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from supabase import AsyncClient
from supa.utils.supabase_helpers import fetch_and_format

from pipecat.processors.frameworks.rtvi import (
    RTVIServerMessageFrame,
)

from genai_single_page_app import GenaiSinglePageApp


OLDEST_CONVERSATION_DATETIME = datetime.now(timezone.utc) - timedelta(weeks=2)


async def show_text_on_screen(params: FunctionCallParams):
    logger.info(f"Showing text on screen: {params.arguments['text']}")
    if params.arguments.get("clear_pre_text"):
        await params.llm.push_frame(
            RTVIServerMessageFrame(data={"clear-pre-text": True})
        )
    await params.llm.push_frame(
        RTVIServerMessageFrame(data={"display-pre-text": params.arguments["text"]})
    )
    await params.result_callback({"result": "success"})


show_text_on_screen_schema = FunctionSchema(
    name="show_text_on_screen",
    description="Show the user text on the screen. Call this function if the user asks you to show them a list of their tasks, priorities, or other information.",
    properties={
        "text": {
            "description": "The text to show the user. This is preformatted text with line breaks and section separators.",
            "type": "string",
        },
        "clear_pre_text": {
            "description": "Clear any existing preformatted text before adding the new text to the display area.",
            "type": "boolean",
        },
    },
    required=["text"],
)


async def generate_single_page_app(params: FunctionCallParams):
    """Generate a single page app from a prompt and stream the results."""
    prompt = params.arguments.get("prompt", "")
    logger.info(f"Generating single page app with prompt: {prompt}")

    # immediately send success to caller
    await params.result_callback({"result": "success"})

    # stream the model output
    async for chunk in await params.llm.aio.models.generate_content_stream(
        model="gemini-2.5-pro-preview-05-06", contents=prompt
    ):
        text = getattr(chunk, "text", "")
        if not text:
            continue
        await params.llm.push_frame(
            RTVIServerMessageFrame(data={"display-pre-text": text})
        )


generate_single_page_app_schema = FunctionSchema(
    name="generate_single_page_app",
    description="Generate a single page app using Google Generative AI.",
    properties={
        "prompt": {
            "description": "Prompt used for single page app generation",
            "type": "string",
        }
    },
    required=["prompt"],
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
            self._gen_app = GenaiSinglePageApp()

            logger.debug(f"gen app schema {generate_single_page_app_schema}")

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
                tools=ToolsSchema(
                    standard_tools=[
                        show_text_on_screen_schema,
                        generate_single_page_app_schema,
                    ],
                    custom_tools={AdapterType.GEMINI: [{"google_search": {}}]},
                ),
            )
            self._llm_service.register_function(
                "show_text_on_screen", show_text_on_screen
            )
            self._llm_service.register_function(
                "generate_single_page_app", self._gen_app.generate_single_page_app
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
