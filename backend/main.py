"""Kaam backend.

Proxies browser microphone audio to Prisma (browsers can't set the custom
headers Prisma needs, and this keeps the API key off the client) and relays
transcripts back. Also exposes Timbre TTS so the app can talk to the worker,
and stores finished interviews.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, questions, tts
from .stt import FINAL_EVENTS, PrismaStream

log = logging.getLogger("kaam")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

app = FastAPI(title="Kaam")

AUDIO_CACHE = config.ROOT / "out" / "cache" / "questions"
INTERVIEWS = config.ROOT / "data" / "interviews"


def _check_lang(lang: str) -> None:
    if lang not in questions.LANGUAGES:
        raise HTTPException(status_code=404, detail=f"Unsupported language: {lang}")


@app.get("/api/health")
async def health():
    return {"ok": True, "key_configured": bool(config.GNANI_API_KEY)}


@app.get("/api/languages")
async def languages():
    return [{"code": code, **info} for code, info in questions.LANGUAGES.items()]


@app.get("/api/questions/{lang}")
async def interview_questions(lang: str):
    _check_lang(lang)
    return questions.questions_for(lang)


@app.get("/api/questions/{lang}/{index}/audio")
async def question_audio(lang: str, index: int):
    """Spoken question, synthesized once and cached on disk to save credits."""
    _check_lang(lang)
    qs = questions.questions_for(lang)
    if not 0 <= index < len(qs):
        raise HTTPException(status_code=404, detail="No such question")
    path = AUDIO_CACHE / f"{config.TTS_MODEL}-{config.TTS_VOICE}-{lang}-{qs[index]['id']}.wav"
    if not path.exists():
        try:
            audio = await tts.synthesize(qs[index]["text"], lang)
        except (tts.TTSError, RuntimeError) as e:
            raise HTTPException(status_code=502, detail=str(e))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(audio)
    return Response(content=path.read_bytes(), media_type="audio/wav")


class SpeakRequest(BaseModel):
    text: str
    language: str = "hi-IN"
    voice: str | None = None


@app.post("/api/tts")
async def speak(req: SpeakRequest):
    try:
        audio = await tts.synthesize(req.text, req.language, voice=req.voice or config.TTS_VOICE)
    except (tts.TTSError, RuntimeError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    return Response(content=audio, media_type="audio/wav")


class Answer(BaseModel):
    question_id: str
    question: str
    transcript: str
    detected_languages: list[str] = []


class Interview(BaseModel):
    language: str
    consent: bool
    answers: list[Answer] = Field(min_length=1)


@app.post("/api/interviews")
async def save_interview(interview: Interview):
    _check_lang(interview.language)
    if not interview.consent:
        raise HTTPException(status_code=400, detail="Consent is required")
    interview_id = uuid.uuid4().hex[:10]
    record = {
        "id": interview_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **interview.model_dump(),
    }
    INTERVIEWS.mkdir(parents=True, exist_ok=True)
    (INTERVIEWS / f"{interview_id}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2))
    return {"id": interview_id}


@app.websocket("/ws/listen")
async def listen(browser: WebSocket, lang: str | None = None):
    """Browser sends PCM16 mono audio at STT_SAMPLE_RATE; we send back Prisma events.

    Text frames from the browser: "flush" sends trailing silence so Prisma
    finalizes the last segment, then replies {"type": "flushed"}.
    """
    await browser.accept()
    stt_lang = questions.stt_lang_for(lang) if lang in questions.LANGUAGES else config.STT_LANG
    try:
        prisma = PrismaStream(lang=stt_lang)
        await prisma.connect()
    except Exception as e:
        log.warning("Prisma connect failed: %s", e)
        await browser.send_json({"type": "error", "message": f"Could not reach Prisma: {e}"})
        await browser.close()
        return

    async def browser_to_prisma():
        while True:
            msg = await browser.receive()
            if msg["type"] == "websocket.disconnect":
                return
            if msg.get("bytes"):
                await prisma.send_audio(msg["bytes"])
            elif msg.get("text") == "flush":
                await prisma.flush()
                await browser.send_json({"type": "flushed"})

    async def prisma_to_browser():
        async for event in prisma.events():
            if event.get("type") in FINAL_EVENTS:
                log.info("[%s] %s", event.get("detected_language_code", "?"), event.get("text"))
            await browser.send_json(event)

    tasks = [asyncio.create_task(browser_to_prisma()), asyncio.create_task(prisma_to_browser())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    except WebSocketDisconnect:
        pass
    finally:
        for t in tasks:
            t.cancel()
        await prisma.close()


app.mount("/", StaticFiles(directory=config.ROOT / "frontend", html=True), name="frontend")
