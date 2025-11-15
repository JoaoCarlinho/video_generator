"""Audio Engine Service - Background music generation.

This service generates background music using Replicate's MusicGen model,
creating mood-appropriate audio for product videos.
"""

import logging
from typing import Optional
import replicate
import aiohttp
import boto3
from pathlib import Path
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


# ============================================================================
# Audio Engine Service
# ============================================================================

class AudioEngine:
    """Generates background music using Replicate MusicGen."""

    def __init__(
        self,
        replicate_api_token: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        s3_bucket_name: str,
        aws_region: str = "us-east-1",
    ):
        """Initialize with API credentials."""
        self.api_token = replicate_api_token
        replicate.api_token = replicate_api_token

        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )
        self.s3_bucket_name = s3_bucket_name
        self.aws_region = aws_region

    async def generate_background_music(
        self,
        mood: str,
        duration: float,
        project_id: str,
        tempo: str = "moderate",
    ) -> str:
        """
        Generate background music for video.

        Args:
            mood: Music mood/genre (e.g., "uplifting", "energetic", "calm", "modern")
            duration: Music duration in seconds
            project_id: Project UUID for S3 storage
            tempo: Tempo description ("slow", "moderate", "fast")

        Returns:
            S3 URL of generated music file
        """
        logger.info(f"Generating {mood} background music ({duration}s)")

        try:
            # Create music prompt
            prompt = self._create_music_prompt(mood, duration, tempo)

            # Generate music via MusicGen
            music_url = await self._call_musicgen_model(prompt, duration)

            # Download and upload to S3
            s3_url = await self._save_music_to_s3(music_url, project_id, mood)

            logger.info(f"✅ Generated music: {s3_url}")
            return s3_url

        except Exception as e:
            logger.error(f"Error generating music: {e}")
            raise

    def _create_music_prompt(self, mood: str, duration: float, tempo: str) -> str:
        """Create music generation prompt."""
        mood_descriptions = {
            "uplifting": "bright, positive, inspiring, motivational",
            "energetic": "dynamic, exciting, fast-paced, powerful",
            "calm": "peaceful, soothing, relaxing, gentle",
            "modern": "contemporary, sleek, trendy, sophisticated",
            "playful": "fun, lighthearted, whimsical, joyful",
            "dramatic": "intense, cinematic, epic, powerful",
            "corporate": "professional, confident, polished, business",
        }

        tempo_descriptions = {
            "slow": "slow tempo, around 60 BPM",
            "moderate": "moderate tempo, around 100 BPM",
            "fast": "fast tempo, around 140 BPM",
        }

        mood_text = mood_descriptions.get(mood.lower(), mood)
        tempo_text = tempo_descriptions.get(tempo.lower(), "moderate tempo")

        prompt = (
            f"Background music for product video advertisement. "
            f"Mood: {mood_text}. "
            f"{tempo_text}. "
            f"Duration: {int(duration)} seconds. "
            f"Instrumental music, no vocals. "
            f"Professional quality, suitable for commercial use."
        )

        logger.debug(f"Music prompt: {prompt}")
        return prompt

    async def _call_musicgen_model(self, prompt: str, duration: float) -> str:
        """Call Replicate MusicGen model."""
        try:
            logger.info("Calling MusicGen model...")

            # MusicGen model parameters
            duration_sec = int(min(duration, 30))  # Cap at 30 seconds

            # Using replicate.run for synchronous call
            # Using the correct version hash: eedcfb (not feedee9)
            output = replicate.run(
                "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb",
                input={
                    "top_k": 250,
                    "top_p": 0,
                    "prompt": prompt,
                    "duration": duration_sec,
                    "temperature": 1,
                    "continuation": False,
                    "model_version": "stereo-large",
                    "output_format": "mp3",
                    "continuation_start": 0,
                    "multi_band_diffusion": False,
                    "normalization_strategy": "peak",
                    "classifier_free_guidance": 3,
                },
                wait=True,
            )

            if isinstance(output, list) and len(output) > 0:
                music_url = output[0]
            else:
                music_url = output

            logger.info(f"MusicGen output: {music_url}")
            return str(music_url)

        except Exception as e:
            logger.error(f"Replicate API error: {e}")
            raise

    async def _save_music_to_s3(self, music_url: str, project_id: str, mood: str) -> str:
        """Download music from Replicate and upload to S3."""
        try:
            # Download audio
            async with aiohttp.ClientSession() as session:
                async with session.get(music_url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status != 200:
                        raise ValueError(f"Failed to download music: HTTP {resp.status}")

                    audio_data = await resp.read()

            # Upload to S3 (S3 RESTRUCTURING: Use new project folder structure)
            s3_key = f"projects/{project_id}/draft/music/music_{mood}.mp3"

            self.s3_client.put_object(
                Bucket=self.s3_bucket_name,
                Key=s3_key,
                Body=audio_data,
                ContentType="audio/mpeg",
                # ACL removed - bucket doesn't allow ACLs, use bucket policy instead
            )

            s3_url = f"https://{self.s3_bucket_name}.s3.{self.aws_region}.amazonaws.com/{s3_key}"

            logger.info(f"✅ Music uploaded to S3: {s3_url}")
            return s3_url

        except Exception as e:
            logger.error(f"Error saving music: {e}")
            raise

    async def generate_music_variants(
        self,
        moods: list,
        duration: float,
        project_id: str,
    ) -> dict:
        """
        Generate multiple music variants.

        Args:
            moods: List of moods to generate
            duration: Duration for each
            project_id: Project ID

        Returns:
            Dict mapping mood to S3 URL
        """
        logger.info(f"Generating {len(moods)} music variants...")

        variants = {}

        for mood in moods:
            try:
                url = await self.generate_background_music(
                    mood=mood,
                    duration=duration,
                    project_id=project_id,
                )
                variants[mood] = url
            except Exception as e:
                logger.error(f"Failed to generate {mood} music: {e}")
                variants[mood] = None

        logger.info(f"✅ Generated {len([v for v in variants.values() if v])} music variants")
        return variants

