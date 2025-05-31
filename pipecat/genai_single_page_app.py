from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams
from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame
from loguru import logger
import os

# google generative ai imports
from google import genai

system_instruction = """
You are an expert AI programmer specialized in generating single page JavaScript apps.

The code you produce will be run inside an iframe in a web browser. 

Output the full text of the single-page app, including HTML, inline css, and inline JavaScript.

Output only the single-page app. Do not output any additional text.

In general, keep your apps simple and focus on what the user needs to do based on the prompt.

As an example, here is a very simple app.

<html>
<head>
    <title>Simple App</title>
</head>
<body>
    <h1 name="title"></h1>
</body>

<script>
    const title = document.querySelector('h1[name="title"]');
    title.textContent = "Hello, World!";
</script>
</html>

"""


class GenaiSinglePageApp:
    """Helper service to generate a single page app using Google's GenAI."""

    def __init__(self):
        # initialize the genai client
        self._client = genai.Client(
            api_key=os.getenv("GOOGLE_API_KEY"),
            http_options=genai.types.HttpOptions(api_version="v1alpha"),
        )

    async def generate_single_page_app(self, params: FunctionCallParams):
        """Generate a single page app from a prompt and stream the results."""
        prompt = params.arguments.get("prompt", "")
        logger.info(f"Generating single page app with prompt: {prompt}")

        # immediately send success to caller
        await params.result_callback({"result": "success"})
        await params.llm.push_frame(
            RTVIServerMessageFrame(data={"display-pre-text": "Generating app..."})
        )
        await params.llm.push_frame(
            RTVIServerMessageFrame(data={"web-application-start": True})
        )

        try:
            # stream the model output
            async for chunk in await self._client.aio.models.generate_content_stream(
                # model="gemini-2.5-pro-preview-05-06",
                model="gemini-2.5-flash-preview-05-20",
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    thinking_config=genai.types.ThinkingConfig(
                        include_thoughts=False, thinking_budget=0
                    ),
                ),
                contents=prompt,
            ):
                text = getattr(chunk, "text", "")
                logger.debug(f"Generated chunk: {text}")
                if not text:
                    continue
                await params.llm.push_frame(
                    RTVIServerMessageFrame(data={"web-application-code": text})
                )
        except Exception as e:
            await params.llm.push_frame(
                RTVIServerMessageFrame(data={"web-application-end": True})
            )
            logger.error(f"Error generating single page app: {e}")
            await params.llm.push_frame(
                RTVIServerMessageFrame(data={"display-pre-text": f"Error: {e}"})
            )
            return
        await params.llm.push_frame(
            RTVIServerMessageFrame(data={"web-application-end": True})
        )

    def generate_single_page_app_schema(self):
        return FunctionSchema(
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
