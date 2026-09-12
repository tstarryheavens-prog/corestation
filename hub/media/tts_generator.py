#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ContentHub TTS Generator
========================
ショート動画（YouTube Shorts / TikTok / Reels）用の高品質AIナレーション音声を
完全無料・自動で生成するモジュール。
macOS標準の say コマンドおよび edge-tts の両対応。
"""

import os
import sys
import subprocess
import argparse
import shutil

def generate_voice(text, output_file, lang="ja", voice=None):
    """
    Generate audio file from text using macOS say or edge-tts.
    """
    ext = os.path.splitext(output_file)[1].lower()
    
    # Check if edge-tts is installed and runnable
    has_edge_tts = shutil.which("edge-tts") is not None

    if has_edge_tts:
        # Default voice mapping for edge-tts
        selected_voice = voice or ("ja-JP-NanamiNeural" if lang == "ja" else "en-US-ChristopherNeural")
        cmd = ["edge-tts", "--voice", selected_voice, "--text", text, "--write-media", output_file]
        print(f"🎙️ Generating voice via edge-tts ({selected_voice})...")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"✅ Voice generated: {output_file}")
            return True
        else:
            print(f"⚠️ edge-tts failed ({res.stderr}), falling back to macOS say...")

    # Fallback to macOS say command
    if sys.platform == "darwin" and shutil.which("say"):
        # Select default macOS voice
        selected_voice = voice or ("Kyoko" if lang == "ja" else "Samantha")
        
        # say natively supports .aiff, .m4a
        tmp_output = output_file if ext in [".aiff", ".m4a"] else output_file + ".aiff"
        
        cmd = ["say", "-v", selected_voice, "-o", tmp_output, text]
        print(f"🎙️ Generating voice via macOS say ({selected_voice})...")
        res = subprocess.run(cmd, capture_output=True, text=True)
        
        if res.returncode == 0:
            # If user wanted .mp3 and ffmpeg is available, convert it
            if ext == ".mp3" and shutil.which("ffmpeg"):
                conv_cmd = ["ffmpeg", "-y", "-i", tmp_output, "-acodec", "libmp3lame", output_file]
                subprocess.run(conv_cmd, capture_output=True)
                if os.path.exists(tmp_output) and tmp_output != output_file:
                    os.remove(tmp_output)
            print(f"✅ Voice generated: {output_file if os.path.exists(output_file) else tmp_output}")
            return True
        else:
            print(f"❌ say command failed: {res.stderr}")
            return False

    print("❌ Error: No compatible TTS engine found (requires macOS say or edge-tts).")
    return False

def main():
    parser = argparse.ArgumentParser(description="ContentHub Audio Generator for Shorts")
    parser.add_argument("--text", help="Text to speak")
    parser.add_argument("--file", help="Text file to read from")
    parser.add_argument("--out", default="hub/output/narration.m4a", help="Output audio path (.m4a, .aiff, .mp3)")
    parser.add_argument("--lang", choices=["ja", "en"], default="ja", help="Language")
    parser.add_argument("--voice", help="Specific voice name (e.g. Kyoko, Samantha)")

    args = parser.parse_args()

    text_to_speak = args.text
    if args.file and os.path.exists(args.file):
        with open(args.file, "r", encoding="utf-8") as f:
            text_to_speak = f.read()

    if not text_to_speak:
        print("Error: Either --text or --file is required.")
        sys.exit(1)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    generate_voice(text_to_speak, args.out, lang=args.lang, voice=args.voice)

if __name__ == "__main__":
    main()
