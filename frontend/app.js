const listenBtn = document.getElementById("listen");
const statusEl = document.getElementById("status");
const transcriptEl = document.getElementById("transcript");

let session = null;

function setStatus(text, kind = "") {
  statusEl.textContent = text;
  statusEl.className = `status ${kind}`;
}

function addLine(text, lang) {
  const li = document.createElement("li");
  if (lang) {
    const tag = document.createElement("span");
    tag.className = "lang";
    tag.textContent = lang;
    li.append(tag);
  }
  li.append(text);
  transcriptEl.append(li);
  transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

async function startListening() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/listen`);
  ws.binaryType = "arraybuffer";

  const stream = await navigator.mediaDevices.getUserMedia({
    // Keep the raw speakerphone signal; browser voice processing tends to
    // suppress audio that comes from another device's loudspeaker.
    audio: { channelCount: 1, echoCancellation: false, noiseSuppression: false, autoGainControl: true },
  });
  const ctx = new AudioContext();
  await ctx.audioWorklet.addModule("pcm-worklet.js");
  const source = ctx.createMediaStreamSource(stream);
  const worklet = new AudioWorkletNode(ctx, "pcm-worklet");
  worklet.port.onmessage = (e) => {
    if (ws.readyState === WebSocket.OPEN) ws.send(e.data);
  };
  source.connect(worklet);

  ws.onopen = () => setStatus("Listening…", "live");
  ws.onmessage = (e) => {
    const event = JSON.parse(e.data);
    switch (event.type) {
      case "speech_start": setStatus("Hearing speech…", "live"); break;
      case "processing": setStatus("Transcribing…", "live"); break;
      case "transcript":
        setStatus("Listening…", "live");
        if (event.text) addLine(event.text, event.detected_language_code);
        break;
      case "error": setStatus(event.message || "Error", "error"); break;
    }
  };
  ws.onclose = () => stopListening(false);

  session = { ws, stream, ctx };
  listenBtn.textContent = "Stop";
  listenBtn.classList.add("live");
}

function stopListening(closeSocket = true) {
  if (!session) return;
  const { ws, stream, ctx } = session;
  session = null;
  stream.getTracks().forEach((t) => t.stop());
  ctx.close();
  if (closeSocket && ws.readyState === WebSocket.OPEN) ws.close();
  listenBtn.textContent = "Start listening";
  listenBtn.classList.remove("live");
  if (!statusEl.classList.contains("error")) setStatus("Idle");
}

listenBtn.addEventListener("click", async () => {
  if (session) return stopListening();
  try {
    setStatus("Connecting…");
    await startListening();
  } catch (err) {
    setStatus(err.message, "error");
    stopListening();
  }
});

document.getElementById("speak").addEventListener("click", async () => {
  const text = document.getElementById("tts-text").value.trim();
  const language = document.getElementById("tts-lang").value;
  if (!text) return;
  const resp = await fetch("/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language }),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    setStatus(body.detail || `TTS failed (${resp.status})`, "error");
    return;
  }
  const url = URL.createObjectURL(await resp.blob());
  new Audio(url).play();
});
