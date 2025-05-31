from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams
from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame
from loguru import logger
import os

# google generative ai imports
from google import generativeai as genai
from google.generativeai import types


class GenaiSinglePageApp:
    """Helper service to generate a single page app using Google's GenAI."""

    def __init__(self):
        # initialize the genai client
        self._client = genai.Client(
            api_key=os.getenv('GOOGLE_API_KEY'),
            http_options=types.HttpOptions(api_version='v1alpha'),
        )

    async def generate_single_page_app(self, params: FunctionCallParams):
        """Generate a single page app from a prompt and stream the results."""
        prompt = params.arguments.get("prompt", "")
        logger.info(f"Generating single page app with prompt: {prompt}")

        # immediately send success to caller
        await params.result_callback({"result": "success"})

        # stream the model output
        async for chunk in await self._client.aio.models.generate_content_stream(
            model='gemini-2.5-pro-preview-05-06', contents=prompt
        ):
            text = getattr(chunk, 'text', '')
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
