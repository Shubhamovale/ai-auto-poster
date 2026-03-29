from pathlib import Path

from generate_content import generate_post_content


def generate_ai_content():
    return generate_post_content()


def load_topics():
    topics_file = Path("topics.json")
    if topics_file.exists():
        return topics_file.read_text(encoding="utf-8")
    return ""
