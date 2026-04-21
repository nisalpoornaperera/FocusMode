#!/usr/bin/env python3
"""Remove YouTube block from hosts file"""
import os
import sys

HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
MARKER = "# FocusMode"

def remove_youtube_blocks():
    try:
        with open(HOSTS_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Remove all FocusMode-SOCIAL entries (including YouTube)
        lines = content.split("\n")
        filtered = [l for l in lines if f"{MARKER}-SOCIAL" not in l]
        new_content = "\n".join(filtered)
        
        with open(HOSTS_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        # Flush DNS
        os.system("ipconfig /flushdns >nul 2>&1")
        print("✓ YouTube and social media blocks removed!")
        return True
    except PermissionError:
        print("❌ Permission denied. Run as Administrator.")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    remove_youtube_blocks()
