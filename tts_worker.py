import sys
import asyncio
import subprocess
import edge_tts

# 1. Keep your exact CLI argument parsing logic
text = sys.argv[1] if len(sys.argv) > 1 else ""

if not text.strip():
    sys.exit(0)

async def stream_neural_audio():
    # Choose a highly realistic, fluid human voice
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    
    # Spawn mpv (native on Arch) to read the stream directly from standard input (fd://0)
    # This plays the speech straight through PipeWire or PulseAudio without creating files.
    player = subprocess.Popen(
        ["mpv", "--no-video", "--cache=no", "fd://0"], 
        stdin=subprocess.PIPE, 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.DEVNULL
    )
    
    try:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                player.stdin.write(chunk["data"])
    except Exception:
        pass
    finally:
        if player.stdin:
            player.stdin.close()
        player.wait()

if __name__ == "__main__":
    # Run the worker synchronously so the FastAPI subprocess monitor keeps tracking its lifecycle perfectly.
    asyncio.run(stream_neural_audio())