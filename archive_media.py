import os

import cloudinary
import cloudinary.uploader


def is_archive_enabled():
    return all(
        os.environ.get(name)
        for name in (
            "CLOUDINARY_CLOUD_NAME",
            "CLOUDINARY_API_KEY",
            "CLOUDINARY_API_SECRET",
        )
    )


def archive_run(video_path, prompt_path=None, metadata_path=None):
    if not is_archive_enabled():
        print("☁️ Cloud archive skipped: Cloudinary secrets not configured.")
        return {}

    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
        api_key=os.environ["CLOUDINARY_API_KEY"],
        api_secret=os.environ["CLOUDINARY_API_SECRET"],
        secure=True,
    )

    run_id = os.environ.get("GITHUB_RUN_ID", "local-run")
    folder = f"ai-auto-poster/{run_id}"
    archived = {}

    print("☁️ Uploading generated assets to Cloudinary...")

    archived["video"] = cloudinary.uploader.upload(
        video_path,
        resource_type="video",
        folder=folder,
        public_id="reel_video",
        overwrite=True,
    )

    if prompt_path and os.path.exists(prompt_path):
        archived["prompt"] = cloudinary.uploader.upload(
            prompt_path,
            resource_type="raw",
            folder=folder,
            public_id="reel_video_prompt",
            overwrite=True,
        )

    if metadata_path and os.path.exists(metadata_path):
        archived["metadata"] = cloudinary.uploader.upload(
            metadata_path,
            resource_type="raw",
            folder=folder,
            public_id="reel_video_metadata",
            overwrite=True,
        )

    print("✅ Cloud archive complete.")
    return archived
