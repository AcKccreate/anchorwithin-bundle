"""
YouTube Uploader — uploads videos via YouTube Data API v3 (OAuth2).
Falls back to saving locally if credentials are missing or auth fails.
"""

import os
import sys
import shutil
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import (YOUTUBE_CLIENT_SECRETS, YOUTUBE_TOKEN_PATH,
                    READY_TO_UPLOAD_DIR, UPLOAD_PRIVACY)


def _get_youtube_service():
    """Build and return an authenticated YouTube API service, or None."""
    if not YOUTUBE_CLIENT_SECRETS or not os.path.exists(YOUTUBE_CLIENT_SECRETS):
        print("[uploader] No YouTube client secrets configured — skipping upload")
        return None

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
        creds = None

        if os.path.exists(YOUTUBE_TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(YOUTUBE_TOKEN_PATH, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(YOUTUBE_CLIENT_SECRETS, SCOPES)
                creds = flow.run_local_server(port=0)

            with open(YOUTUBE_TOKEN_PATH, "w") as f:
                f.write(creds.to_json())

        return build("youtube", "v3", credentials=creds)

    except Exception as e:
        print(f"[uploader] YouTube auth failed: {e}")
        return None


def upload_to_youtube(video_path: str, title: str, description: str,
                      tags: list = None, thumbnail_path: str = None,
                      privacy: str = None) -> dict:
    """
    Upload a video to YouTube as unlisted (FENRIR protocol).

    Returns:
        {"uploaded": True/False, "video_id": str or None, "url": str or None,
         "local_path": str or None}
    """
    privacy = privacy or UPLOAD_PRIVACY
    result = {"uploaded": False, "video_id": None, "url": None, "local_path": None}

    youtube = _get_youtube_service()
    if youtube:
        try:
            from googleapiclient.http import MediaFileUpload

            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags or [],
                    "categoryId": "10",  # Music category
                },
                "status": {
                    "privacyStatus": privacy,
                    "selfDeclaredMadeForKids": False,
                },
            }

            media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            response = None
            while response is None:
                _, response = request.next_chunk()

            video_id = response["id"]
            result["uploaded"] = True
            result["video_id"] = video_id
            result["url"] = f"https://youtu.be/{video_id}"

            # Set thumbnail if provided
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    youtube.thumbnails().set(
                        videoId=video_id,
                        media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg"),
                    ).execute()
                except Exception as e:
                    print(f"[uploader] Thumbnail upload failed: {e}")

            print(f"[uploader] Uploaded: {result['url']}")
            return result

        except Exception as e:
            print(f"[uploader] Upload failed: {e}")

    # Fallback: save to local ready_to_upload directory
    READY_TO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    local_video = str(READY_TO_UPLOAD_DIR / Path(video_path).name)
    shutil.copy2(video_path, local_video)
    result["local_path"] = local_video

    # Save metadata alongside
    meta_path = local_video + ".meta.json"
    with open(meta_path, "w") as f:
        json.dump({
            "title": title,
            "description": description,
            "tags": tags or [],
            "privacy": privacy,
            "thumbnail": thumbnail_path,
        }, f, indent=2)

    print(f"[uploader] Saved locally: {local_video}")
    return result


if __name__ == "__main__":
    print("[uploader] Module loaded OK.")
    print(f"  YouTube secrets configured: {bool(YOUTUBE_CLIENT_SECRETS)}")
    print(f"  Ready-to-upload dir: {READY_TO_UPLOAD_DIR}")
