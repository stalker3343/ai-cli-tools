#!/usr/bin/env python3
"""
VK Video downloader using yt-dlp.
Usage:
    python download_vk.py <vk_video_url> [options]

Options:
    --audio-only          Download audio track only (mp3)
    --output-dir <path>   Output directory (default: current dir)
    --cookies <file>      Path to cookies.txt exported from browser (use vk.com cookies)
    --browser <name>      Browser to extract cookies from: chrome, firefox, edge (default: chrome)

Examples:
    python download_vk.py "https://vkvideo.ru/video-195818952_456239930" --cookies vk.com_cookies.txt
    python download_vk.py "https://vkvideo.ru/video-195818952_456239930" --audio-only --cookies vk.com_cookies.txt

How to get vk.com_cookies.txt:
    1. Install Chrome extension "Get cookies.txt LOCALLY"
    2. Go to vk.com (make sure you are logged in)
    3. Click the extension -> Export -> save as vk.com_cookies.txt
"""

import argparse
import subprocess
import sys
import os


def download_vk_video(
    url: str,
    audio_only: bool = False,
    output_dir: str = ".",
    cookies_file: str | None = None,
    browser: str = "chrome",
):
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

    cmd = [sys.executable, "-m", "yt_dlp", "--output", output_template]

    if cookies_file:
        cmd += ["--cookies", os.path.abspath(cookies_file)]
    else:
        cmd += ["--cookies-from-browser", browser]

    if audio_only:
        cmd += [
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",
        ]
    else:
        cmd += [
            "--format", "bestvideo+bestaudio/best",
            "--merge-output-format", "mp4",
        ]

    cmd.append(url)

    mode = "audio only (mp3)" if audio_only else "video (mp4)"
    auth = f"cookies file: {cookies_file}" if cookies_file else f"browser: {browser}"
    print(f"Downloading: {url}")
    print(f"Mode: {mode} | Auth: {auth}")
    print(f"Output dir: {output_dir}\n")

    result = subprocess.run(cmd)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Download VK Video via yt-dlp")
    parser.add_argument("url", help="VK video URL")
    parser.add_argument("--audio-only", action="store_true", help="Download audio track only (mp3)")
    parser.add_argument("--output-dir", default=".", help="Output directory (default: current dir)")
    parser.add_argument("--cookies", metavar="FILE", help="Path to cookies.txt exported from browser")
    parser.add_argument("--browser", default="chrome", help="Browser to extract cookies from (default: chrome)")
    args = parser.parse_args()

    success = download_vk_video(
        args.url,
        audio_only=args.audio_only,
        output_dir=args.output_dir,
        cookies_file=args.cookies,
        browser=args.browser,
    )
    if not success:
        print("\nFailed. Tips:")
        print("  - If 'cookies error': export cookies.txt from browser extension and use --cookies cookies.txt")
        print("  - If 'only available to followers': make sure you are logged in VK in the browser")
        sys.exit(1)


if __name__ == "__main__":
    main()
