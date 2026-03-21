# ai-auto-poster
Automated AI content poster for Facebook &amp; YouTube

The content generator now also creates a `video_prompt` field for AI video tools.
When you run the poster, it saves:

- `output/reel_video_prompt.txt`
- `output/reel_video_metadata.json`
- `output/reel_video.mp4`

The `.txt` prompt is ready to paste into a text-to-video model, while the local `.mp4`
remains the current fallback slideshow renderer.

This repo is already set up for cloud execution through GitHub Actions 3 times a day:

- 9:00 AM IST
- 1:00 PM IST
- 7:00 PM IST

The workflow installs dependencies on GitHub-hosted runners, runs `poster.py`, posts to
Facebook and YouTube, and uploads the generated `output/` files as workflow artifacts.

Required GitHub Actions secrets:

- `GEMINI_API_KEY`
- `UNSPLASH_ACCESS_KEY`
- `FB_PAGE_ID`
- `FB_PAGE_ACCESS_TOKEN`
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

Optional free cloud archive:

- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`

If Cloudinary is configured, each scheduled run also uploads the generated video, prompt,
and metadata so the assets are preserved on the web instead of living only on the runner.
