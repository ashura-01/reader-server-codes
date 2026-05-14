from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from groq import Groq
import subprocess
import sys
import threading
import pyttsx3
import os
from typing import Optional

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

# Load Groq API key from file
def load_groq_api_key():
    try:
        with open("groq_api.txt", "r") as f:
            api_key = f.read().strip()
            if not api_key:
                raise ValueError("API key file is empty")
            return api_key
    except FileNotFoundError:
        print("❌ Error: groq_api.txt file not found!")
        return None
    except Exception as e:
        print(f"❌ Error reading groq_api.txt: {e}")
        return None

# Initialize Groq client
api_key = load_groq_api_key()
if api_key:
    groq_client = Groq(api_key=api_key)
else:
    groq_client = None
    print("⚠️  Groq client not initialized. /explain, /summarize, and /answer endpoints will not work.")

def get_explanation_from_groq(content: str) -> Optional[str]:
    """Send content to Groq API and get an explanation"""
    if not groq_client:
        return "Groq API is not configured. Please check your API key file."
    
    try:
        prompt = f"""You are a factual explainer. Your job is to explain ONLY what is present in the content below.

STRICT RULES:
- Explain ONLY what is explicitly stated in the provided content.
- Do NOT add any information, facts, or examples that are not in the content.
- Do NOT assume, infer, or invent anything beyond what is written.
- If a concept in the content is unclear, say it is unclear — do not guess.
- Keep the explanation conversational and suitable for reading aloud.
- Length: 2–3 short paragraphs.

CONTENT TO EXPLAIN:
{content}

EXPLANATION (based strictly on the content above):"""

        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict factual assistant. "
                        "Never add information that is not present in the user-provided content. "
                        "If you are unsure, say so explicitly. Do not hallucinate."
                    )
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=1000,
        )
        
        explanation = chat_completion.choices[0].message.content
        return explanation
        
    except Exception as e:
        print(f"❌ Groq API error: {e}")
        return f"Sorry, I couldn't generate an explanation due to an error: {str(e)}"

def get_summary_from_groq(content: str, summary_length: str = "medium") -> Optional[str]:
    """Send content to Groq API and get a summary"""
    if not groq_client:
        return "Groq API is not configured. Please check your API key file."
    
    length_settings = {
        "short": "1-2 sentences (very concise, key points only)",
        "medium": "1 short paragraph (3-5 sentences)",
        "long": "2-3 paragraphs (comprehensive but concise)"
    }
    
    length_desc = length_settings.get(summary_length, length_settings["medium"])
    
    try:
        prompt = f"""You are a factual summarizer. Summarize ONLY what is written in the content below.

STRICT RULES:
- Use ONLY information that is explicitly present in the content.
- Do NOT add outside knowledge, opinions, or invented details.
- Do NOT rephrase in a way that changes the meaning.
- If something is ambiguous, reflect that ambiguity — do not resolve it with a guess.
- Length: {length_desc}.
- Keep it clear and suitable for reading aloud.

CONTENT TO SUMMARIZE:
{content}

SUMMARY (strictly based on the content above):"""

        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict factual summarizer. "
                        "Only summarize what is in the provided content. "
                        "Never add, invent, or assume information. Do not hallucinate."
                    )
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=800,
        )
        
        summary = chat_completion.choices[0].message.content
        return summary
        
    except Exception as e:
        print(f"❌ Groq API error: {e}")
        return f"Sorry, I couldn't generate a summary due to an error: {str(e)}"

def get_answer_from_groq(question: str, context: str = "") -> Optional[str]:
    """Send a question to Groq API and get a direct answer"""
    if not groq_client:
        return "Groq API is not configured. Please check your API key file."
    
    try:
        if context:
            prompt = f"""Answer the question using ONLY the information in the context below.

STRICT RULES:
- Base your answer entirely on the provided context.
- If the context does not contain enough information to answer, say exactly: "The context does not contain enough information to answer this question."
- Do NOT use outside knowledge or make assumptions beyond the context.
- Be direct and concise. Do not add filler phrases.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:"""
        else:
            prompt = f"""Answer the following question directly and accurately.

STRICT RULES:
- Only state what you know with confidence.
- If you are not sure about something, say "I'm not certain, but..." or "I don't know."
- Do NOT invent facts, names, dates, or figures.
- Be concise. No filler phrases like "Great question!" or "I'll answer that."

QUESTION:
{question}

ANSWER:"""

        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict factual assistant. "
                        "Never fabricate information. "
                        "If you don't know something or the context doesn't cover it, say so clearly. "
                        "Do not hallucinate."
                    )
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=500,
        )
        
        answer = chat_completion.choices[0].message.content
        return answer
        
    except Exception as e:
        print(f"❌ Groq API error: {e}")
        return f"Sorry, I couldn't generate an answer due to an error: {str(e)}"

def start_tts_process(text):
    import os
    text = str(text).replace('\x00', '')
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    worker_script = os.path.join(script_dir, 'tts_worker.py')
    
    return subprocess.Popen([sys.executable, worker_script, text])

def monitor_process(proc: subprocess.Popen):
    """Monitor TTS process and update status when done"""
    global current_proc, reading_status
    proc.wait()
    with proc_lock:
        if current_proc == proc:
            current_proc = None
            reading_status = False

@app.post("/explain")
async def explain_and_read(req: Request):
    """Endpoint that takes content, generates explanation via Groq, and reads it aloud"""
    global current_proc, reading_status
    
    if not groq_client:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Groq API not configured. Check groq_api.txt file."}
        )
    
    data = await req.json()
    content = data.get("content", "").strip()
    
    if not content:
        return {"status": "error", "message": "No content provided"}
    
    explanation = get_explanation_from_groq(content)
    
    if not explanation:
        return {"status": "error", "message": "Failed to generate explanation"}
    
    with proc_lock:
        if current_proc and current_proc.poll() is None:
            current_proc.terminate()
        
        current_proc = start_tts_process(explanation)
        reading_status = True
        threading.Thread(target=monitor_process, args=(current_proc,), daemon=True).start()
    
    return {
        "status": "reading",
        "explanation": explanation,
        "length": len(explanation)
    }

@app.post("/summarize")
async def summarize_and_read(req: Request):
    """Endpoint that takes content, generates a summary via Groq, and reads it aloud"""
    global current_proc, reading_status
    
    if not groq_client:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Groq API not configured. Check groq_api.txt file."}
        )
    
    data = await req.json()
    content = data.get("content", "").strip()
    summary_length = data.get("length", "medium")
    
    if not content:
        return {"status": "error", "message": "No content provided"}
    
    summary = get_summary_from_groq(content, summary_length)
    
    if not summary:
        return {"status": "error", "message": "Failed to generate summary"}
    
    with proc_lock:
        if current_proc and current_proc.poll() is None:
            current_proc.terminate()
        
        current_proc = start_tts_process(summary)
        reading_status = True
        threading.Thread(target=monitor_process, args=(current_proc,), daemon=True).start()
    
    return {
        "status": "reading",
        "summary": summary,
        "length": len(summary),
        "summary_type": summary_length
    }

@app.post("/answer")
async def answer_question(req: Request):
    """Endpoint that takes a question (with optional context) and reads the answer aloud"""
    global current_proc, reading_status
    
    if not groq_client:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Groq API not configured. Check groq_api.txt file."}
        )
    
    data = await req.json()
    question = data.get("question", "").strip()
    context = data.get("context", "").strip()
    
    if not question:
        return {"status": "error", "message": "No question provided"}
    
    answer = get_answer_from_groq(question, context)
    
    if not answer:
        return {"status": "error", "message": "Failed to generate answer"}
    
    with proc_lock:
        if current_proc and current_proc.poll() is None:
            current_proc.terminate()
        
        current_proc = start_tts_process(answer)
        reading_status = True
        threading.Thread(target=monitor_process, args=(current_proc,), daemon=True).start()
    
    return {
        "status": "reading",
        "answer": answer,
        "length": len(answer)
    }

@app.post("/answer-stream")
async def answer_question_stream(req: Request):
    """Alternative endpoint that streams the answer"""
    global current_proc, reading_status
    
    if not groq_client:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Groq API not configured"}
        )
    
    data = await req.json()
    question = data.get("question", "").strip()
    context = data.get("context", "").strip()
    
    if not question:
        return {"status": "error", "message": "No question provided"}
    
    if context:
        prompt = f"""Answer the question using ONLY the information in the context below.

STRICT RULES:
- Base your answer entirely on the provided context.
- If the context does not contain enough information, say exactly: "The context does not contain enough information to answer this question."
- Do NOT use outside knowledge or make assumptions.
- Be direct and concise.

CONTEXT: {context}

QUESTION: {question}

ANSWER:"""
    else:
        prompt = f"""Answer the following question directly and accurately.

STRICT RULES:
- Only state what you know with confidence.
- If unsure, say "I'm not certain" or "I don't know."
- Do NOT invent facts, names, dates, or figures.
- No filler phrases.

QUESTION: {question}

ANSWER:"""
    
    try:
        stream = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict factual assistant. "
                        "Never fabricate information. "
                        "If you don't know or the context doesn't cover it, say so clearly. "
                        "Do not hallucinate."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=500,
            stream=True,
        )
        
        full_answer = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                full_answer += chunk.choices[0].delta.content
        
        full_answer = full_answer.strip()
        intro_phrases = [
            "I'll answer that:", "Here's my answer:", "The answer is:",
            "Let me answer that:", "I'll help you with that:"
        ]
        for phrase in intro_phrases:
            if full_answer.startswith(phrase):
                full_answer = full_answer[len(phrase):].strip()
        
        with proc_lock:
            if current_proc and current_proc.poll() is None:
                current_proc.terminate()
            
            current_proc = start_tts_process(full_answer)
            reading_status = True
            threading.Thread(target=monitor_process, args=(current_proc,), daemon=True).start()
        
        return {
            "status": "reading",
            "answer": full_answer,
            "length": len(full_answer)
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/summarize-stream")
async def summarize_and_read_stream(req: Request):
    """Alternative endpoint that streams the summary"""
    global current_proc, reading_status
    
    if not groq_client:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Groq API not configured"}
        )
    
    data = await req.json()
    content = data.get("content", "").strip()
    summary_length = data.get("length", "medium")
    
    if not content:
        return {"status": "error", "message": "No content provided"}
    
    length_settings = {
        "short": "1-2 sentences (very concise, key points only)",
        "medium": "1 short paragraph (3-5 sentences)",
        "long": "2-3 paragraphs (comprehensive but concise)"
    }
    
    length_desc = length_settings.get(summary_length, length_settings["medium"])
    
    prompt = f"""Summarize ONLY what is written in the content below.

STRICT RULES:
- Use ONLY information explicitly present in the content.
- Do NOT add outside knowledge or invented details.
- Length: {length_desc}.

CONTENT: {content}

SUMMARY:"""
    
    try:
        stream = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict factual summarizer. "
                        "Only summarize what is in the provided content. "
                        "Never add, invent, or assume information. Do not hallucinate."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=800,
            stream=True,
        )
        
        full_summary = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                full_summary += chunk.choices[0].delta.content
        
        with proc_lock:
            if current_proc and current_proc.poll() is None:
                current_proc.terminate()
            
            current_proc = start_tts_process(full_summary)
            reading_status = True
            threading.Thread(target=monitor_process, args=(current_proc,), daemon=True).start()
        
        return {
            "status": "reading",
            "summary": full_summary,
            "length": len(full_summary),
            "summary_type": summary_length
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/read")
async def read_text(req: Request):
    """Original endpoint: directly read any text without Groq explanation/summary"""
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

@app.get("/health")
async def health_check():
    """Check if Groq API is configured"""
    return {
        "status": "healthy",
        "groq_configured": groq_client is not None,
        "api_key_file_exists": os.path.exists("groq_api.txt")
    }