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
    _build_visual_world,
    create_background_music,
    create_generated_scene_clip,
    create_subtitle_overlay,
    create_transition_flash,
    create_voiceover,
    split_sentences,
)


def build_scene_durations(total_duration, spoken_beats):
    scene_count = max(len(spoken_beats), 1)
    word_counts = [max(2, len(re.findall(r"\w+", beat))) for beat in spoken_beats]
    if not word_counts:
        word_counts = [8]
    total_words = sum(word_counts)
    min_duration = 0.95 if scene_count >= 8 else 1.05
    max_duration = 1.85 if scene_count >= 8 else 2.2
    durations = [
        max(min_duration, min(max_duration, total_duration * (count / total_words)))
        for count in word_counts
    ]
    scale = total_duration / sum(durations)
    durations = [duration * scale for duration in durations]
    if durations:
        durations[0] = max(1.2, min(1.9, durations[0]))
        durations[-1] = max(1.0, min(1.6, durations[-1]))
        scale = total_duration / sum(durations)
        durations = [duration * scale for duration in durations]
    return durations


def normalize_scene_plan(content):
    scene_plan = (content.get("scene_plan") or [])[:10]
    if scene_plan:
        return scene_plan

    keywords = (content.get("scene_keywords") or [])[:10]
    if not keywords:
        keywords = [content["topic"]]

    subtitles = content.get("subtitle_lines") or split_sentences(content["voiceover_script"])
    subtitles = [line for line in subtitles if line][:10]
    if len(subtitles) < 8:
        subtitles = subtitles + [content["hook"]] * (8 - len(subtitles))

    scene_count = min(max(len(subtitles), len(keywords), 8), 10)
    scene_keywords = (keywords * scene_count)[:scene_count]
    subtitles = (subtitles * scene_count)[:scene_count]
    transitions = ["cut", "push", "cut", "flash", "slide", "cut", "zoom", "cut", "flash", "fade"]
    return [
        {
            "visual_keyword": scene_keywords[index],
            "subtitle": subtitles[index],
            "line": subtitles[index],
            "transition": transitions[index % len(transitions)],
        }
        for index in range(scene_count)
    ]


def apply_transition_to_clip(clip, transition):
    transition = (transition or "cut").lower()
    if transition == "push":
        return clip.resize(lambda t: 1.02 + (0.06 * min(max(t / max(clip.duration, 0.01), 0), 1)))
    if transition == "zoom":
        return clip.resize(lambda t: 1.04 + (0.10 * min(max(t / max(clip.duration, 0.01), 0), 1)))
    if transition == "slide":
        return clip.set_position(lambda t: (0, int(-40 * min(max(t / max(clip.duration, 0.01), 0), 1))))
    if transition == "flash":
        return clip.fx(lambda c: c.fadein(0.06).fadeout(0.06))
    if transition == "fade":
        return clip.fadein(0.12).fadeout(0.12)
    return clip.fadein(0.05).fadeout(0.05)


def build_transition_flash(transition, duration):
    transition = (transition or "cut").lower()
    if transition == "flash":
        return create_transition_flash(duration, color=(255, 248, 220), opacity=0.24)
    if transition in {"push", "zoom"}:
        return create_transition_flash(duration, color=(255, 255, 255), opacity=0.14)
    if transition == "slide":
        return create_transition_flash(duration, color=(200, 235, 255), opacity=0.12)
    return None


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
    output_dir = os.path.join(os.getcwd(), "output")
    metadata_path, script_path, outline_path = save_story_assets(output_dir, content)

    voice_path = create_voiceover(
        content["voiceover_script"],
        os.path.join(output_dir, "story_voiceover.mp3"),
    )
    voiceover = AudioFileClip(voice_path)
    target_duration = max(15.0, min(30.0, voiceover.duration + 0.6))

    scene_plan = normalize_scene_plan(content)

    spoken_beats = [
        item.get("line") or item.get("subtitle") or content["hook"]
        for item in scene_plan
    ]
    scene_durations = build_scene_durations(target_duration, spoken_beats)

    clips = []
    lead_scene = scene_plan[0] if scene_plan else {}
    visual_world = _build_visual_world(
        lead_scene.get("visual_keyword") or content["topic"],
        lead_scene.get("visual_direction") or content["title"],
    )
    for index, scene in enumerate(scene_plan):
        scene_duration = scene_durations[index]
        keyword = scene.get("visual_keyword") or scene.get("visual_direction") or content["topic"]
        visual_direction = scene.get("visual_direction") or keyword
        clip = create_generated_scene_clip(
            keyword,
            visual_direction,
            scene_duration,
            index,
            visual_world=visual_world,
        )
        transition = scene.get("transition")
        clip = apply_transition_to_clip(clip, transition)
        subtitle = scene.get("subtitle") or content["hook"]
        subtitle_clip = create_subtitle_overlay(subtitle, scene_duration)
        layers = [clip, subtitle_clip.set_position(("center", "bottom"))]
        flash_clip = build_transition_flash(transition, scene_duration)
        if flash_clip is not None:
            layers.append(flash_clip)
        composed = CompositeVideoClip(layers).set_duration(scene_duration)
        clips.append(composed)

    final_video = concatenate_videoclips(clips, method="compose").set_duration(target_duration)
    voiceover = voiceover.set_start(0).volumex(1.0)
    music = create_background_music(target_duration).set_duration(target_duration).volumex(0.16)
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
    mixed_audio.close()
    voiceover.close()
    final_video.close()

    return output_path, metadata_path, script_path, outline_path
