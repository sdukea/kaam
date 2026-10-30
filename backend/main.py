"""Kaam backend.

Proxies browser microphone audio to Prisma (browsers can't set the custom
headers Prisma needs, and this keeps the API key off the client) and relays
transcripts back. Also exposes Timbre TTS so the app can talk to the worker.
"""

import asyncio
import logging

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, tts
from .stt import PrismaStream

log = logging.getLogger("kaam")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

app = FastAPI(title="Kaam")


@app.get("/api/health")
async def health():
    return {"ok": True, "key_configured": bool(config.GNANI_API_KEY)}


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


@app.websocket("/ws/listen")
async def listen(browser: WebSocket):
    """Browser sends PCM16 mono audio at STT_SAMPLE_RATE; we send back Prisma events."""
    await browser.accept()
    try:
        prisma = PrismaStream()
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
            elif msg.get("text") == "commit":
                await prisma.commit()

    async def prisma_to_browser():
        async for event in prisma.events():
            if event.get("type") == "transcript":
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
