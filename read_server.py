from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
import subprocess
import sys
import threading
import html
import re

app = FastAPI()

# Restrict CORS (allow only specific origins instead of "*")
ALLOWED_ORIGINS = ["http://localhost", "https://yourdomain.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"]
)

current_proc = None
proc_lock = threading.Lock()
reading_status = False


# -------- SECURITY HELPERS -------- #

def sanitize_text(text: str) -> str:
    """
    Prevent command injection, HTML/script payloads, and overly large input.
    """
    # Limit size to prevent DoS
    if len(text) > 500:
        raise HTTPException(status_code=413, detail="Input too long")

    # Escape HTML/script payloads
    text = html.escape(text)

    # Remove backticks and shell-like characters
    text = re.sub(r"[;|&<>`$]", "", text)

    return text.strip()


# -------- REQUEST MODEL -------- #

class TTSRequest(BaseModel):
    text: str

    @field_validator("text")
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError("Text cannot be empty")
        return v


# -------- PROCESS HANDLERS -------- #

def start_tts_process(text: str):
    safe_text = sanitize_text(text)
    
    code = (
        # No shell, no user-controlled eval
        "import pyttsx3;"
        "e=pyttsx3.init();"
        "e.setProperty('rate',170);"
        "e.setProperty('volume',1.0);"
        f"e.say({safe_text!r});"
        "e.runAndWait()"
    )

    # shell=False protects against injection
    return subprocess.Popen([sys.executable, "-c", code], shell=False)


def monitor_process(proc: subprocess.Popen):
    global current_proc, reading_status
    proc.wait()
    with proc_lock:
        if current_proc == proc:
            current_proc = None
            reading_status = False


# -------- ROUTES -------- #

@app.post("/read")
async def read_text(payload: TTSRequest):
    global current_proc, reading_status

    text = payload.text

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
