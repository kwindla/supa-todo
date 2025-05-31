FROM dailyco/pipecat-base:latest

COPY ./requirements.txt requirements.txt

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./supa ./supa
COPY ./system-instruction.txt system-instruction.txt
COPY ./gemini_live.py gemini_live.py
COPY ./bot.py bot.py
