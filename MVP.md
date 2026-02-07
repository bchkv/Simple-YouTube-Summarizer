# MVP

## Goal
Single CLI command that:
YouTube URL → transcript → summarized via macOS Shortcut.

## In scope
- One executable shell script
- English captions via yt-dlp
- Summarization performed by ChatGPT macOS app
- No API usage

## Build outline
1. Extract captions from a YouTube URL using yt-dlp
2. Convert captions to plain text
3. Pipe transcript into a macOS Shortcut via 
4. Shortcut sends text to ChatGPT and returns a summary
5. Print summary to stdout (or handle via Shortcut)

## Shortcut setup
- Create a Shortcut named 
- Set it to receive text input from Shell Script
- Pass input to ChatGPT with a fixed summarization prompt
- Return the result (clipboard or output)

## Distribution
- Include the exported  file in 
- Users install it by double-clicking the file
- First run may require macOS Automation permissions
