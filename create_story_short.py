import json
import os
import re

from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    VideoFileClip,
    concatenate_videoclips,
)

from create_video import (
    create_background_music,
    create_subtitle_overlay,
    create_voiceover,
    download_file,
    fetch_pexels_video,
    fit_vertical_clip,
    has_pexels_access,
    split_sentences,
)


def build_scene_durations(total_duration, subtitles):
    scene_count = max(len(subtitles), 1)
    word_counts = [max(3, len(re.findall(r"\w+", subtitle))) for subtitle in subtitles]
    if not word_counts:
        word_counts = [8]
    total_words = sum(word_counts)
    durations = [max(3.2, total_duration * (count / total_words)) for count in word_counts]
    scale = total_duration / sum(durations)
    durations = [duration * scale for duration in durations]
    if durations:
        durations[0] = max(4.8, durations[0])
        durations[-1] = max(3.8, durations[-1])
        scale = total_duration / sum(durations)
        durations = [duration * scale for duration in durations]
    return durations


def save_story_assets(output_dir, content):
    os.makedirs(output_dir, exist_ok=True)
    metadata_path = os.path.join(output_dir, "story_short_metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=2)

    script_path = os.path.join(output_dir, "story_voiceover.txt")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(content["voiceover_script"] + "\n")

    outline_path = os.path.join(output_dir, "story_outline.md")
    with open(outline_path, "w", encoding="utf-8") as f:
        f.write(f"# {content['title']}\n\n")
        f.write(f"Topic: {content.get('topic', '')}\n\n")
        f.write(f"Hook: {content.get('hook', '')}\n\n")
        f.write(f"Summary: {content.get('summary', '')}\n\n")
        f.write("## Story Beats\n")
        for beat in content.get("story_beats", []):
            f.write(f"- {beat}\n")
        f.write("\n## Scene Keywords\n")
        for keyword in content.get("scene_keywords", []):
            f.write(f"- {keyword}\n")
        f.write("\n## Subtitle Lines\n")
        for line in content.get("subtitle_lines", []):
            f.write(f"- {line}\n")
        if content.get("source_link"):
            f.write("\n## Source\n")
            f.write(
                f"- {content.get('source_name', '')} ({content.get('source_query', '')})\n"
            )
            f.write(f"- {content['source_link']}\n")

    return metadata_path, script_path, outline_path


def create_story_short(content):
    if not has_pexels_access():
        raise RuntimeError("PEXELS_API_KEY is required for story shorts.")

    output_dir = os.path.join(os.getcwd(), "output")
    metadata_path, script_path, outline_path = save_story_assets(output_dir, content)

    voice_path = create_voiceover(
        content["voiceover_script"],
        os.path.join(output_dir, "story_voiceover.mp3"),
    )
    voiceover = AudioFileClip(voice_path)
    target_duration = max(45.0, min(75.0, voiceover.duration + 2.0))

    keywords = (content.get("scene_keywords") or [])[:10]
    if not keywords:
        keywords = [content["topic"]]

    subtitles = content.get("subtitle_lines") or split_sentences(content["voiceover_script"])
    subtitles = subtitles[:10]
    if len(subtitles) < 8:
        subtitles = subtitles + [content["hook"]] * (8 - len(subtitles))

    scene_count = min(max(len(subtitles), len(keywords), 8), 10)
    scene_keywords = (keywords * scene_count)[:scene_count]
    subtitles = (subtitles * scene_count)[:scene_count]
    scene_durations = build_scene_durations(target_duration, subtitles)

    downloaded = []
    clips = []
    for index, keyword in enumerate(scene_keywords):
        link = fetch_pexels_video(keyword)
        if not link:
            raise RuntimeError(f"No stock video found for keyword: {keyword}")
        clip_path = os.path.join(output_dir, f"story_scene_{index + 1}.mp4")
        downloaded.append(download_file(link, clip_path))

    for index, clip_path in enumerate(downloaded):
        base_clip = VideoFileClip(clip_path)
        scene_duration = scene_durations[index]
        clip = fit_vertical_clip(base_clip, scene_duration)
        subtitle = subtitles[index] if index < len(subtitles) else content["hook"]
        subtitle_clip = create_subtitle_overlay(subtitle, scene_duration)
        composed = CompositeVideoClip(
            [clip, subtitle_clip.set_position(("center", "bottom"))]
        ).set_duration(scene_duration)
        clips.append(composed)

    final_video = concatenate_videoclips(clips, method="compose").set_duration(target_duration)
    voiceover = voiceover.set_start(0).volumex(1.0)
    music = create_background_music(target_duration).set_duration(target_duration).volumex(0.18)
    mixed_audio = CompositeAudioClip([music, voiceover]).set_duration(target_duration)
    final_video = final_video.set_audio(mixed_audio)

    output_path = os.path.join(output_dir, "story_short.mp4")
    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=os.path.join(output_dir, "story_temp_audio.m4a"),
        remove_temp=True,
        logger=None,
    )

    for clip in clips:
        clip.close()
    for path in downloaded:
        if os.path.exists(path):
            os.remove(path)
    mixed_audio.close()
    voiceover.close()
    final_video.close()

    return output_path, metadata_path, script_path, outline_path
