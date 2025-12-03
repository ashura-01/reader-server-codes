from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import sys
import threading

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

current_proc = None
proc_lock = threading.Lock()
reading_status = False


def start_tts_process(text: str):
    code = (
        "import pyttsx3;"
        f"e=pyttsx3.init();"
        "e.setProperty('rate',170);"
        "e.setProperty('volume',1.0);"
        f"e.say({text!r});"
        "e.runAndWait()"
    )
    return subprocess.Popen([sys.executable, "-c", code])


def monitor_process(proc: subprocess.Popen):
    global current_proc, reading_status
    proc.wait()  # wait until TTS finishes
    with proc_lock:
        if current_proc == proc:
            current_proc = None
            reading_status = False


@app.post("/read")
async def read_text(req: Request):
    global current_proc, reading_status

    data = await req.json()
    text = data.get("text", "").strip()
    if not text:
        return {"status": "no text"}

    with proc_lock:
        if current_proc and current_proc.poll() is None:
            current_proc.terminate()

        current_proc = start_tts_process(text)
        reading_status = True
        threading.Thread(target=monitor_process, args=(current_proc,), daemon=True).start()

    return {"status": "reading"}


@app.post("/stop")
async def stop_reading():
    global current_proc, reading_status

    with proc_lock:
        if current_proc and current_proc.poll() is None:
            current_proc.terminate()
            current_proc = None
        reading_status = False

    return {"status": "stopped"}


@app.get("/status")
async def get_status():
    return {"reading": reading_status}
