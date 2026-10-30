// Kaam guided voice interview: Timbre asks each question out loud, the worker
// answers, Prisma transcribes live, and the answer stays editable.

const $ = (id) => document.getElementById(id);

const state = {
  lang: null,
  questions: [],
  index: 0,
  answers: [],
  mic: null,     // { stream, ctx }
  ws: null,      // Prisma session for the current answer
  pending: 0,    // speech segments Prisma has started but not yet returned
  detected: new Set(),
  audio: null,
};

function show(screen) {
  for (const id of ["welcome", "interview", "done"]) $(`screen-${id}`).hidden = id !== screen;
}

function setMic(text, live = false) {
  $("mic-status").textContent = text;
  $("mic-dot").classList.toggle("live", live);
}

// ---------- Welcome ----------

async function loadLanguages() {
  const langs = await (await fetch("/api/languages")).json();
  for (const { code, label } of langs) {
    const btn = document.createElement("button");
    btn.textContent = label;
    btn.setAttribute("aria-pressed", "false");
    btn.addEventListener("click", () => {
      state.lang = code;
      for (const b of $("languages").children) b.setAttribute("aria-pressed", String(b === btn));
      updateStart();
    });
    $("languages").append(btn);
  }
}

function updateStart() {
  $("start").disabled = !(state.lang && $("consent").checked);
}

$("consent").addEventListener("change", updateStart);

$("start").addEventListener("click", async () => {
  $("welcome-error").hidden = true;
  try {
    await startMic();
    state.questions = await (await fetch(`/api/questions/${state.lang}`)).json();
    state.index = 0;
    state.answers = [];
    show("interview");
    askQuestion();
  } catch (err) {
    $("welcome-error").textContent = `Could not start: ${err.message}`;
    $("welcome-error").hidden = false;
  }
});

// ---------- Microphone ----------

async function startMic() {
  if (state.mic) return;
  const stream = await navigator.mediaDevices.getUserMedia({
    // Keep the raw signal: Prisma is trained on noisy audio, and browser noise
    // suppression can clip quiet speech.
    audio: { channelCount: 1, echoCancellation: false, noiseSuppression: false, autoGainControl: true },
  });
  const ctx = new AudioContext();
  await ctx.audioWorklet.addModule("pcm-worklet.js");
  const worklet = new AudioWorkletNode(ctx, "pcm-worklet");
  worklet.port.onmessage = (e) => {
    if (state.ws && state.ws.readyState === WebSocket.OPEN && state.ws.listening) state.ws.send(e.data);
  };
  ctx.createMediaStreamSource(stream).connect(worklet);
  state.mic = { stream, ctx };
}

function stopMic() {
  if (!state.mic) return;
  state.mic.stream.getTracks().forEach((t) => t.stop());
  state.mic.ctx.close();
  state.mic = null;
}

// ---------- Interview ----------

function playQuestion() {
  return new Promise((resolve) => {
    if (state.audio) state.audio.pause();
    const audio = new Audio(`/api/questions/${state.lang}/${state.index}/audio`);
    state.audio = audio;
    audio.onended = resolve;
    audio.onerror = resolve; // the question is on screen even if audio fails
    audio.play().catch(resolve);
  });
}

async function askQuestion() {
  const q = state.questions[state.index];
  const total = state.questions.length;
  $("question").textContent = q.text;
  $("progress-label").textContent = `Question ${state.index + 1} of ${total}`;
  $("progress-bar").style.width = `${(state.index / total) * 100}%`;
  $("answer").value = "";
  $("next").textContent = state.index === total - 1 ? "Finish" : "Next";
  state.detected = new Set();

  setMic("Listen to the question…");
  setButtons(false);
  await playQuestion();
  await startAnswer();
  setButtons(true);
}

function setButtons(enabled) {
  for (const id of ["next", "rerecord", "replay"]) $(id).disabled = !enabled;
}

function startAnswer() {
  return new Promise((resolve) => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws/listen?lang=${encodeURIComponent(state.lang)}`);
    ws.listening = false;
    state.ws = ws;
    state.pending = 0;

    ws.onopen = () => {
      ws.listening = true;
      setMic("Listening… speak now", true);
      resolve();
    };
    ws.onmessage = (e) => {
      const event = JSON.parse(e.data);
      if (event.type === "speech_start") state.pending++;
      if (event.type === "transcript") {
        state.pending = Math.max(0, state.pending - 1);
        if (event.detected_language_code) state.detected.add(event.detected_language_code);
        if (event.text) {
          const box = $("answer");
          box.value = box.value ? `${box.value.trimEnd()} ${event.text}` : event.text;
        }
      }
      if (event.type === "error") setMic(event.message || "Speech service error");
      ws.dispatchEvent(new CustomEvent("kaam", { detail: event }));
    };
    ws.onerror = () => {
      setMic("Could not connect to speech service");
      resolve();
    };
  });
}

// Stop sending audio, let Prisma finish the last segment, then close.
function finishAnswer() {
  const ws = state.ws;
  state.ws = null;
  if (!ws || ws.readyState !== WebSocket.OPEN) return Promise.resolve();
  ws.listening = false;
  setMic("Finishing…");

  return new Promise((resolve) => {
    const done = () => { clearTimeout(timer); ws.close(); resolve(); };
    const timer = setTimeout(done, 4000);
    let flushed = false;
    ws.addEventListener("kaam", (e) => {
      if (e.detail.type === "flushed") flushed = true;
      if (flushed && state.pending === 0) setTimeout(done, 300);
    });
    ws.send("flush");
  });
}

function discardAnswer() {
  if (state.ws) state.ws.close();
  state.ws = null;
}

$("next").addEventListener("click", async () => {
  setButtons(false);
  await finishAnswer();
  const q = state.questions[state.index];
  state.answers.push({
    question_id: q.id,
    question: q.text,
    transcript: $("answer").value.trim(),
    detected_languages: [...state.detected],
  });
  state.index++;
  if (state.index < state.questions.length) {
    askQuestion();
  } else {
    finishInterview();
  }
});

$("rerecord").addEventListener("click", async () => {
  setButtons(false);
  discardAnswer();
  $("answer").value = "";
  state.detected = new Set();
  await startAnswer();
  setButtons(true);
});

$("replay").addEventListener("click", async () => {
  setButtons(false);
  if (state.ws) state.ws.listening = false;
  setMic("Listen to the question…");
  await playQuestion();
  if (state.ws) {
    state.ws.listening = true;
    setMic("Listening… speak now", true);
  }
  setButtons(true);
});

// ---------- Done ----------

async function finishInterview() {
  stopMic();
  show("done");
  $("review").replaceChildren(...state.answers.map((a) => {
    const li = document.createElement("li");
    const q = document.createElement("div");
    q.className = "q";
    q.textContent = a.question;
    const t = document.createElement("div");
    t.textContent = a.transcript || "(no answer)";
    li.append(q, t);
    return li;
  }));

  $("saved").textContent = "Saving…";
  const resp = await fetch("/api/interviews", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ language: state.lang, consent: true, answers: state.answers }),
  });
  if (resp.ok) {
    const { id } = await resp.json();
    $("saved").textContent = `Saved as interview ${id}. Resume generation is coming next.`;
  } else {
    $("saved").textContent = `Could not save (${resp.status}).`;
  }
}

$("restart").addEventListener("click", () => location.reload());

loadLanguages();
