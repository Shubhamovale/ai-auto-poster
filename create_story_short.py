import json
import os
import re
import math

from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    VideoFileClip,
    concatenate_videoclips,
)

from create_video import (
    _build_visual_world,
    build_motion_clip,
    create_background_music,
    create_generated_scene_clip,
    build_hera_scene_prompt,
    create_hud_overlay,
    create_subtitle_overlay,
    create_transition_flash,
    create_text_frame,
    create_voiceover,
    build_veo_scene_prompt,
    fetch_background_image,
    fit_vertical_clip,
    generate_hera_scene_video,
    generate_veo_scene_video,
    split_sentences,
)

HERA_SCENE_COUNT = int(os.environ.get("HERA_SCENE_COUNT", "4"))
# Default Veo mode to exactly 3 generated clips, then stitch them into one short.
VEO_SCENE_COUNT = int(os.environ.get("VEO_SCENE_COUNT", "3"))
SHORTS_RENDER_MODE = os.environ.get("SHORTS_RENDER_MODE", "slides").strip().lower()


def build_scene_durations(total_duration, spoken_beats, end_pad=0.0):
    scene_count = max(len(spoken_beats), 1)
    end_pad = max(0.0, float(end_pad or 0.0))
    spoken_duration = max(0.1, float(total_duration) - end_pad)
    word_counts = []
    for beat in spoken_beats:
        text = " ".join((beat or "").split())
        word_count = max(2, len(re.findall(r"\w+", text)))
        # Give slightly more weight to longer lines so visual changes track the real spoken pace better.
        char_weight = max(0, len(text) - 18) / 24.0
        punctuation_weight = 0.35 * len(re.findall(r"[,:;!?-]", text))
        word_counts.append(word_count + char_weight + punctuation_weight)
    if not word_counts:
        word_counts = [8]
    total_words = sum(word_counts)
    min_duration = 0.95 if scene_count >= 8 else 1.05
    max_duration = 1.85 if scene_count >= 8 else 2.2
    durations = [
        max(min_duration, min(max_duration, spoken_duration * (count / total_words)))
        for count in word_counts
    ]
    scale = spoken_duration / sum(durations)
    durations = [duration * scale for duration in durations]
    if durations:
        durations[0] = max(1.2, min(1.9, durations[0]))
        durations[-1] = max(1.0, min(1.6, durations[-1]))
        scale = spoken_duration / sum(durations)
        durations = [duration * scale for duration in durations]
        durations[-1] += end_pad
    return durations


def group_story_scenes(scene_plan, scene_durations, target_groups):
    scene_count = len(scene_plan)
    if scene_count == 0:
        return []

    target_groups = max(1, min(target_groups, scene_count))
    beats_per_group = math.ceil(scene_count / target_groups)
    groups = []
    for start in range(0, scene_count, beats_per_group):
        end = min(start + beats_per_group, scene_count)
        groups.append(
            {
                "start": start,
                "end": end,
                "scenes": scene_plan[start:end],
                "durations": scene_durations[start:end],
            }
        )
    return groups


def build_group_prompt(group, scene_index):
    scenes = group["scenes"]
    primary = scenes[0]
    scene_types = [scene.get("scene_type") or "abstract" for scene in scenes]
    group_scene_type = scene_types[0]
    if "cta" in scene_types:
        group_scene_type = "cta"
    elif "hook" in scene_types:
        group_scene_type = "hook"
    elif "product_reveal" in scene_types:
        group_scene_type = "product_reveal"
    elif "interface" in scene_types or "feature_demo" in scene_types:
        group_scene_type = "interface"

    beat_text = " ".join(
        " ".join((scene.get("line") or scene.get("subtitle") or "").split())
        for scene in scenes
    )
    visual_direction = " ".join(
        " ".join((scene.get("visual_direction") or scene.get("visual_keyword") or "").split())
        for scene in scenes
    )
    subtitle = " / ".join(
        " ".join((scene.get("subtitle") or "").split())
        for scene in scenes
    )
    keyword = primary.get("visual_keyword") or primary.get("visual_direction") or beat_text
    return build_veo_scene_prompt(
        scene_type=group_scene_type,
        keyword=keyword,
        visual_direction=f"{visual_direction}. Story flow: {beat_text}",
        subtitle=subtitle,
        scene_index=scene_index,
    )


def scene_motif(scene):
    scene_type = (scene.get("scene_type") or "").lower()
    combined_text = " ".join(
        [
            scene.get("visual_keyword") or "",
            scene.get("visual_direction") or "",
            scene.get("line") or "",
        ]
    ).lower()
    if scene_type in {"interface", "feature_demo"}:
        return "interface"
    if scene_type in {"product_reveal", "hook"}:
        return "product"
    if scene_type in {"stage", "social_proof"}:
        return "stage"
    if any(term in combined_text for term in ["interface", "screen", "ui", "display", "overlay", "app"]):
        return "interface"
    if any(term in combined_text for term in ["product", "device", "phone", "glasses", "console", "controller"]):
        return "product"
    if any(term in combined_text for term in ["event", "stage", "launch", "keynote", "announcement"]):
        return "stage"
    return None


def render_generated_story_short(content, scene_plan, scene_durations, output_dir, target_duration, voiceover):
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
        layers = [clip, subtitle_clip]
        hud_clip = create_hud_overlay(scene_duration, scene_motif(scene), visual_world)
        if hud_clip is not None:
            layers.append(hud_clip)
        flash_clip = build_transition_flash(transition, scene_duration)
        if flash_clip is not None:
            layers.append(flash_clip)
        composed = CompositeVideoClip(layers).set_duration(scene_duration)
        clips.append(composed)

    final_video = concatenate_videoclips(clips, method="compose").set_duration(target_duration)
    voice_track = voiceover.set_start(0).volumex(1.0)
    music = create_background_music(target_duration).set_duration(target_duration).volumex(0.16)
    mixed_audio = CompositeAudioClip([music, voice_track]).set_duration(target_duration)
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
    final_video.close()
    return output_path


def render_slide_story_short(content, scene_plan, scene_durations, output_dir, target_duration, voiceover):
    clips = []
    background = fetch_background_image(content.get("topic") or content.get("title") or "technology")
    accent_colors = [
        (255, 77, 109),
        (255, 209, 102),
        (6, 214, 160),
        (76, 201, 240),
    ]

    for index, scene in enumerate(scene_plan):
        scene_duration = scene_durations[index]
        subtitle = scene.get("subtitle") or content["hook"]
        line = scene.get("line") or subtitle
        layout = "hook" if index == 0 or (scene.get("scene_type") == "cta") else "standard"
        accent_color = accent_colors[index % len(accent_colors)]
        text_frame = create_text_frame(
            background,
            subtitle,
            subtitle=line,
            text_color="white" if index != 0 else "#FFD700",
            font_size=84 if index == 0 else 72,
            accent_color=accent_color,
            layout=layout,
        )
        slide_clip = build_motion_clip(
            text_frame,
            duration=scene_duration,
            zoom_start=1.0 if index else 1.03,
            zoom_end=1.06 if index else 1.12,
            fade=0.12,
        )
        transition = scene.get("transition")
        slide_clip = apply_transition_to_clip(slide_clip, transition)
        subtitle_clip = create_subtitle_overlay(subtitle, scene_duration)
        layers = [slide_clip, subtitle_clip]
        flash_clip = build_transition_flash(transition, scene_duration)
        if flash_clip is not None:
            layers.append(flash_clip)
        composed = CompositeVideoClip(layers).set_duration(scene_duration)
        clips.append(composed)

    final_video = concatenate_videoclips(clips, method="compose").set_duration(target_duration)
    voice_track = voiceover.set_start(0).volumex(1.0)
    music = create_background_music(target_duration).set_duration(target_duration).volumex(0.16)
    mixed_audio = CompositeAudioClip([music, voice_track]).set_duration(target_duration)
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
    final_video.close()
    return output_path


def render_veo_story_short(content, scene_plan, scene_durations, output_dir, target_duration, voiceover):
    scene_groups = group_story_scenes(scene_plan, scene_durations, 3)
    generated_paths = []
    clips = []

    for index, group in enumerate(scene_groups):
        veo_prompt = build_group_prompt(group, index)
        scene_path = os.path.join(output_dir, f"story_scene_group_{index + 1}.mp4")
        generated_paths.append(generate_veo_scene_video(veo_prompt, scene_path))

    for group, scene_path in zip(scene_groups, generated_paths):
        base_clip = VideoFileClip(scene_path)
        group_scene_count = len(group["scenes"])
        clip_duration = max(float(base_clip.duration or 0), 0.1)
        segment_length = clip_duration / max(group_scene_count, 1)

        for local_index, scene in enumerate(group["scenes"]):
            scene_duration = group["durations"][local_index]
            start = min(segment_length * local_index, max(clip_duration - 0.05, 0))
            end = min(clip_duration, start + segment_length)
            if end - start < 0.2:
                start = 0
                end = clip_duration

            segment_clip = base_clip.subclip(start, end)
            clip = fit_vertical_clip(segment_clip, scene_duration)
            transition = scene.get("transition")
            clip = apply_transition_to_clip(clip, transition)
            subtitle = scene.get("subtitle") or content["hook"]
            subtitle_clip = create_subtitle_overlay(subtitle, scene_duration)
            layers = [clip, subtitle_clip]
            flash_clip = build_transition_flash(transition, scene_duration)
            if flash_clip is not None:
                layers.append(flash_clip)
            composed = CompositeVideoClip(layers).set_duration(scene_duration)
            clips.append(composed)

        base_clip.close()

    final_video = concatenate_videoclips(clips, method="compose").set_duration(target_duration)
    voice_track = voiceover.set_start(0).volumex(1.0)
    music = create_background_music(target_duration).set_duration(target_duration).volumex(0.16)
    mixed_audio = CompositeAudioClip([music, voice_track]).set_duration(target_duration)
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
    for path in generated_paths:
        if os.path.exists(path):
            os.remove(path)
    mixed_audio.close()
    final_video.close()
    return output_path


def render_hera_story_short(content, scene_plan, scene_durations, output_dir, target_duration, voiceover):
    scene_groups = group_story_scenes(scene_plan, scene_durations, HERA_SCENE_COUNT)
    generated_paths = []
    clips = []

    for index, group in enumerate(scene_groups):
        primary = group["scenes"][0]
        scene_types = [scene.get("scene_type") or "abstract" for scene in group["scenes"]]
        group_scene_type = scene_types[0]
        if "cta" in scene_types:
            group_scene_type = "cta"
        elif "hook" in scene_types:
            group_scene_type = "hook"
        elif "interface" in scene_types or "feature_demo" in scene_types:
            group_scene_type = "interface"
        elif "product_reveal" in scene_types:
            group_scene_type = "product_reveal"

        beat_text = " ".join(
            " ".join((scene.get("line") or scene.get("subtitle") or "").split())
            for scene in group["scenes"]
        )
        visual_direction = " ".join(
            " ".join((scene.get("visual_direction") or scene.get("visual_keyword") or "").split())
            for scene in group["scenes"]
        )
        subtitle = " / ".join(
            " ".join((scene.get("subtitle") or "").split())
            for scene in group["scenes"]
        )
        keyword = primary.get("visual_keyword") or primary.get("visual_direction") or content["topic"]
        hera_prompt = build_hera_scene_prompt(
            scene_type=group_scene_type,
            keyword=keyword,
            visual_direction=f"{visual_direction}. Story flow: {beat_text}",
            subtitle=subtitle,
            scene_index=index,
        )
        group_duration = max(2.0, min(12.0, sum(group["durations"]) + 0.4))
        scene_path = os.path.join(output_dir, f"story_scene_hera_{index + 1}.mp4")
        generated_paths.append(generate_hera_scene_video(hera_prompt, scene_path, duration_seconds=group_duration))

    for group, scene_path in zip(scene_groups, generated_paths):
        base_clip = VideoFileClip(scene_path)
        group_scene_count = len(group["scenes"])
        clip_duration = max(float(base_clip.duration or 0), 0.1)
        segment_length = clip_duration / max(group_scene_count, 1)

        for local_index, scene in enumerate(group["scenes"]):
            scene_duration = group["durations"][local_index]
            start = min(segment_length * local_index, max(clip_duration - 0.05, 0))
            end = min(clip_duration, start + segment_length)
            if end - start < 0.2:
                start = 0
                end = clip_duration

            segment_clip = base_clip.subclip(start, end)
            clip = fit_vertical_clip(segment_clip, scene_duration)
            transition = scene.get("transition")
            clip = apply_transition_to_clip(clip, transition)
            subtitle = scene.get("subtitle") or content["hook"]
            subtitle_clip = create_subtitle_overlay(subtitle, scene_duration)
            layers = [clip, subtitle_clip]
            flash_clip = build_transition_flash(transition, scene_duration)
            if flash_clip is not None:
                layers.append(flash_clip)
            composed = CompositeVideoClip(layers).set_duration(scene_duration)
            clips.append(composed)

        base_clip.close()

    final_video = concatenate_videoclips(clips, method="compose").set_duration(target_duration)
    voice_track = voiceover.set_start(0).volumex(1.0)
    music = create_background_music(target_duration).set_duration(target_duration).volumex(0.16)
    mixed_audio = CompositeAudioClip([music, voice_track]).set_duration(target_duration)
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
    for path in generated_paths:
        if os.path.exists(path):
            os.remove(path)
    mixed_audio.close()
    final_video.close()
    return output_path


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
    voice_duration = max(float(voiceover.duration or 0), 0.1)
    target_duration = max(15.0, min(30.0, voice_duration + 0.6))
    end_pad = max(0.0, target_duration - voice_duration)

    scene_plan = normalize_scene_plan(content)

    spoken_beats = [
        item.get("line") or item.get("subtitle") or content["hook"]
        for item in scene_plan
    ]
    scene_durations = build_scene_durations(voice_duration, spoken_beats, end_pad=end_pad)
    if SHORTS_RENDER_MODE == "veo":
        output_path = render_veo_story_short(
            content,
            scene_plan,
            scene_durations,
            output_dir,
            target_duration,
            voiceover,
        )
    elif SHORTS_RENDER_MODE == "hera":
        try:
            output_path = render_hera_story_short(
                content,
                scene_plan,
                scene_durations,
                output_dir,
                target_duration,
                voiceover,
            )
        except Exception as exc:
            print(f"Hera render failed: {exc}. Falling back to slide renderer...")
            output_path = render_slide_story_short(
                content,
                scene_plan,
                scene_durations,
                output_dir,
                target_duration,
                voiceover,
            )
    elif SHORTS_RENDER_MODE == "generated":
        output_path = render_generated_story_short(
            content,
            scene_plan,
            scene_durations,
            output_dir,
            target_duration,
            voiceover,
        )
    else:
        output_path = render_slide_story_short(
            content,
            scene_plan,
            scene_durations,
            output_dir,
            target_duration,
            voiceover,
        )

    voiceover.close()

    return output_path, metadata_path, script_path, outline_path
