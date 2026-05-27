"""
MOCK WINSOUND FOR LINUX TESTING
This file intercepts the `import winsound` call in friction.py so that the app 
can run on Linux without modifying the Windows-only codebase.
"""
def Beep(frequency, duration):
    print(f"\n[LINUX MOCK] 🔊 Audio Ping: Beep({frequency}Hz, {duration}ms)\n")
