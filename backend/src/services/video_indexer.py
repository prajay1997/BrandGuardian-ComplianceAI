'''
connector: Python and Azure Video Indexer
'''

import os
import time
import logging
import requests

# ⭐ CHANGED:
# yt_dlp is no longer required because we are not downloading
# the YouTube video inside this service.
# import yt_dlp

from azure.identity import DefaultAzureCredential

logger = logging.getLogger("video-indexer")


class VideoIndexerService:

    def __init__(self):
        self.account_id = os.getenv("AZURE_VI_ACCOUNT_ID")
        self.location = os.getenv("AZURE_VI_LOCATION")
        self.subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        self.resource_group = os.getenv("AZURE_RESOURCE_GROUP")
        self.vi_name = os.getenv(
            "AZURE_VI_NAME",
            "brand-yt-project-prajay"
        )
        self.credential = DefaultAzureCredential()

    def get_access_token(self):
        """Generates an ARM Access Token."""
        try:
            token_object = self.credential.get_token(
                "https://management.azure.com/.default"
            )
            return token_object.token

        except Exception as e:
            logger.error(f"Failed to get Azure Token: {e}")
            raise

    def get_account_token(self, arm_access_token):
        """Exchanges ARM token for Video Indexer Account Token."""

        url = (
            f"https://management.azure.com/subscriptions/"
            f"{self.subscription_id}"
            f"/resourceGroups/{self.resource_group}"
            f"/providers/Microsoft.VideoIndexer/accounts/"
            f"{self.vi_name}"
            f"/generateAccessToken?api-version=2025-04-01"
        )

        headers = {
            "Authorization": f"Bearer {arm_access_token}"
        }

        payload = {
            "permissionType": "Contributor",
            "scope": "Account"
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            raise Exception(
                f"Failed to get VI Account Token: {response.text}"
            )

        return response.json().get("accessToken")


    # ⭐ CHANGED:
    # Removed download_youtube_video()
    #
    # We don't want Azure App Service to download
    # the YouTube video using yt-dlp anymore.


    # ⭐ CHANGED:
    # This function now accepts a Blob SAS URL instead
    # of a local video file.
    def upload_video_from_url(self, video_url, video_name):
        """
        Uploads a video from a URL to Azure Video Indexer.

        The URL can be an Azure Blob SAS URL.
        """

        arm_token = self.get_access_token()

        vi_token = self.get_account_token(
            arm_token
        )

        api_url = (
            f"https://api.videoindexer.ai/"
            f"{self.location}/Accounts/"
            f"{self.account_id}/Videos"
        )

        params = {
            "accessToken": vi_token,
            "name": video_name,
            "privacy": "Private",
            "indexingPreset": "Default",

            # ⭐ MAIN CHANGE:
            # Instead of sending a local file,
            # we give Video Indexer the Blob SAS URL.
            "videoUrl": video_url
        }

        logger.info(
            "Sending Blob video URL to Azure Video Indexer..."
        )

        response = requests.post(
            api_url,
            params=params
        )

        if response.status_code != 200:
            raise Exception(
                f"Azure Video Indexer Upload Failed: "
                f"{response.text}"
            )

        logger.info(
            "Video successfully submitted to Video Indexer."
        )

        return response.json().get("id")


    def wait_for_processing(self, video_id):
        """Polls status until complete."""

        logger.info(
            f"Waiting for video {video_id} to process..."
        )

        while True:

            arm_token = self.get_access_token()

            vi_token = self.get_account_token(
                arm_token
            )

            url = (
                f"https://api.videoindexer.ai/"
                f"{self.location}/Accounts/"
                f"{self.account_id}/Videos/"
                f"{video_id}/Index"
            )

            params = {
                "accessToken": vi_token
            }

            response = requests.get(
                url,
                params=params
            )

            data = response.json()

            state = data.get("state")

            if state == "Processed":
                return data

            elif state == "Failed":
                raise Exception(
                    "Video Indexing Failed in Azure."
                )

            elif state == "Quarantined":
                raise Exception(
                    "Video Quarantined "
                    "(Copyright/Content Policy Violation)."
                )

            logger.info(
                f"Status: {state}... waiting 30s"
            )

            time.sleep(30)


    def extract_data(self, vi_json):
        """Parses the JSON into our State format."""

        transcript_lines = []

        for v in vi_json.get("videos", []):

            for insight in v.get(
                "insights", {}
            ).get("transcript", []):

                transcript_lines.append(
                    insight.get("text")
                )


        ocr_lines = []

        for v in vi_json.get("videos", []):

            for insight in v.get(
                "insights", {}
            ).get("ocr", []):

                ocr_lines.append(
                    insight.get("text")
                )


        return {
            "transcript": " ".join(
                transcript_lines
            ),

            "ocr_text": ocr_lines,

            "video_metadata": {
                "duration": (
                    vi_json
                    .get("summarizedInsights", {})
                    .get("duration", {})
                    .get("seconds")
                ),

                "platform": "azure_blob"
            }
        }