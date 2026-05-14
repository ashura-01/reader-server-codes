import sys
import pyttsx3

text = sys.argv[1] if len(sys.argv) > 1 else ""
engine = pyttsx3.init()
engine.say(text)
engine.runAndWait()