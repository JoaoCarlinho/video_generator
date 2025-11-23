"""Integration tests for automatic failover logic (Story 1.4).

These tests verify the automatic failover functionality when the primary
video generation provider fails, ensuring transparent failover to the
fallback provider with proper logging and metadata tracking.
"""

import pytest
import logging
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from app.services.video_generator import VideoGenerator
from app.services.providers.base import BaseVideoProvider
from app.services.providers.replicate import ReplicateVideoProvider


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_replicate_provider():
    """Mock ReplicateVideoProvider for testing."""
    provider = AsyncMock(spec=ReplicateVideoProvider)
    provider.get_provider_name.return_value = "replicate"
    provider.health_check.return_value = True
    return provider


@pytest.fixture
def mock_ecs_provider():
    """Mock ECS provider for testing (not implemented yet)."""
    provider = AsyncMock(spec=BaseVideoProvider)
    provider.get_provider_name.return_value = "ecs"
    provider.health_check.return_value = True
    return provider


@pytest.fixture
def sample_prompt():
    """Sample prompt for video generation."""
    return "A serene beach sunset with palm trees swaying gently"


@pytest.fixture
def sample_style_spec():
    """Sample style specification dictionary."""
    return {
        "lighting_direction": "golden hour",
        "camera_style": "cinematic",
        "mood_atmosphere": "peaceful",
        "grade_postprocessing": "warm tones"
    }


# ============================================================================
# Test Primary/Fallback Provider Attributes (AC1, AC2)
# ============================================================================

def test_primary_provider_attribute_exists():
    """Test that VideoGenerator has primary_provider attribute (AC1)."""
    gen = VideoGenerator(provider="replicate")
    assert hasattr(gen, 'primary_provider')
    assert isinstance(gen.primary_provider, BaseVideoProvider)


def test_fallback_provider_attribute_exists():
    """Test that VideoGenerator has fallback_provider attribute (AC1)."""
    gen = VideoGenerator(provider="replicate")
    assert hasattr(gen, 'fallback_provider')


def test_replicate_provider_no_fallback():
    """Test that provider='replicate' sets primary=Replicate, fallback=None (AC2)."""
    gen = VideoGenerator(provider="replicate")
    assert gen.primary_provider.get_provider_name() == "replicate"
    assert gen.fallback_provider is None


def test_ecs_provider_not_implemented_yet():
    """Test that provider='ecs' raises NotImplementedError (pending Story 3.1)."""
    with pytest.raises(NotImplementedError) as exc_info:
        VideoGenerator(provider="ecs")
    assert "ECS provider not yet implemented" in str(exc_info.value)


# ============================================================================
# Test Failover Logic (AC3, AC4)
# ============================================================================

@pytest.mark.asyncio
async def test_primary_succeeds_no_failover(mock_replicate_provider, sample_prompt, sample_style_spec):
    """Test that primary provider success does not trigger failover."""
    # Setup
    video_url = "https://replicate.com/video.mp4"
    mock_replicate_provider.generate_scene_background.return_value = video_url

    # Create VideoGenerator with mocked provider
    with patch('app.services.video_generator.ReplicateVideoProvider', return_value=mock_replicate_provider):
        gen = VideoGenerator(provider="replicate")

        # Execute
        result = await gen.generate_scene_background(
            prompt=sample_prompt,
            style_spec_dict=sample_style_spec,
            duration=5.0
        )

        # Verify
        assert result == video_url
        mock_replicate_provider.generate_scene_background.assert_called_once()
        assert gen.provider_metadata["failover_used"] is False
        assert gen.provider_metadata["primary_provider"] == "replicate"


@pytest.mark.asyncio
async def test_primary_fails_no_fallback_raises_exception(mock_replicate_provider, sample_prompt, sample_style_spec):
    """Test that primary failure with no fallback re-raises exception (AC4)."""
    # Setup - primary provider raises exception
    test_error = RuntimeError("Primary provider unavailable")
    mock_replicate_provider.generate_scene_background.side_effect = test_error

    # Create VideoGenerator with mocked provider (no fallback for replicate)
    with patch('app.services.video_generator.ReplicateVideoProvider', return_value=mock_replicate_provider):
        gen = VideoGenerator(provider="replicate")
        assert gen.fallback_provider is None

        # Execute and verify exception is re-raised
        with pytest.raises(RuntimeError) as exc_info:
            await gen.generate_scene_background(
                prompt=sample_prompt,
                style_spec_dict=sample_style_spec,
                duration=5.0
            )

        assert str(exc_info.value) == "Primary provider unavailable"
        mock_replicate_provider.generate_scene_background.assert_called_once()


@pytest.mark.asyncio
async def test_primary_fails_fallback_succeeds(mock_ecs_provider, mock_replicate_provider, sample_prompt, sample_style_spec, caplog):
    """Test failover from ECS to Replicate when primary fails (AC3, AC4, AC7)."""
    # Setup - primary fails, fallback succeeds
    primary_error = RuntimeError("ECS endpoint timeout")
    fallback_video_url = "https://replicate.com/fallback-video.mp4"

    mock_ecs_provider.generate_scene_background.side_effect = primary_error
    mock_replicate_provider.generate_scene_background.return_value = fallback_video_url

    # Manually create generator with both providers (simulating future ECS implementation)
    with patch('app.services.video_generator.ReplicateVideoProvider', return_value=mock_replicate_provider):
        gen = VideoGenerator(provider="replicate")
        # Manually inject ECS as primary and Replicate as fallback (simulating Story 3.1)
        gen.primary_provider = mock_ecs_provider
        gen.fallback_provider = mock_replicate_provider
        gen.provider_name = "ecs"

        # Execute with logging capture
        with caplog.at_level(logging.WARNING):
            result = await gen.generate_scene_background(
                prompt=sample_prompt,
                style_spec_dict=sample_style_spec,
                duration=5.0
            )

        # Verify fallback was called
        assert result == fallback_video_url
        mock_ecs_provider.generate_scene_background.assert_called_once()
        mock_replicate_provider.generate_scene_background.assert_called_once()

        # Verify metadata (AC5)
        assert gen.provider_metadata["failover_used"] is True
        assert gen.provider_metadata["primary_provider"] == "ecs"
        assert "ECS endpoint timeout" in gen.provider_metadata["failover_reason"]
        assert "timestamp" in gen.provider_metadata

        # Verify logging (AC6)
        assert any("Primary provider (ecs) failed" in record.message for record in caplog.records)
        assert any("Failing over to replicate" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_both_providers_fail_raises_primary_exception(mock_ecs_provider, mock_replicate_provider, sample_prompt, sample_style_spec):
    """Test that both providers failing raises the original primary exception."""
    # Setup - both providers fail
    primary_error = RuntimeError("ECS endpoint timeout")
    fallback_error = RuntimeError("Replicate rate limit exceeded")

    mock_ecs_provider.generate_scene_background.side_effect = primary_error
    mock_replicate_provider.generate_scene_background.side_effect = fallback_error

    # Manually create generator with both providers
    with patch('app.services.video_generator.ReplicateVideoProvider', return_value=mock_replicate_provider):
        gen = VideoGenerator(provider="replicate")
        gen.primary_provider = mock_ecs_provider
        gen.fallback_provider = mock_replicate_provider

        # Execute and verify primary exception is raised
        with pytest.raises(RuntimeError) as exc_info:
            await gen.generate_scene_background(
                prompt=sample_prompt,
                style_spec_dict=sample_style_spec,
                duration=5.0
            )

        # Should raise PRIMARY error, not fallback error
        assert str(exc_info.value) == "ECS endpoint timeout"
        mock_ecs_provider.generate_scene_background.assert_called_once()
        mock_replicate_provider.generate_scene_background.assert_called_once()


# ============================================================================
# Test Provider Metadata Tracking (AC5)
# ============================================================================

@pytest.mark.asyncio
async def test_metadata_tracks_primary_provider_name(mock_replicate_provider, sample_prompt, sample_style_spec):
    """Test that metadata tracks primary_provider name (AC5)."""
    video_url = "https://replicate.com/video.mp4"
    mock_replicate_provider.generate_scene_background.return_value = video_url

    with patch('app.services.video_generator.ReplicateVideoProvider', return_value=mock_replicate_provider):
        gen = VideoGenerator(provider="replicate")
        await gen.generate_scene_background(sample_prompt, sample_style_spec, 5.0)

        assert "primary_provider" in gen.provider_metadata
        assert gen.provider_metadata["primary_provider"] == "replicate"


@pytest.mark.asyncio
async def test_metadata_tracks_failover_used_false_on_success(mock_replicate_provider, sample_prompt, sample_style_spec):
    """Test that metadata shows failover_used=False when primary succeeds (AC5)."""
    video_url = "https://replicate.com/video.mp4"
    mock_replicate_provider.generate_scene_background.return_value = video_url

    with patch('app.services.video_generator.ReplicateVideoProvider', return_value=mock_replicate_provider):
        gen = VideoGenerator(provider="replicate")
        await gen.generate_scene_background(sample_prompt, sample_style_spec, 5.0)

        assert gen.provider_metadata["failover_used"] is False
        assert gen.provider_metadata["failover_reason"] is None


@pytest.mark.asyncio
async def test_metadata_tracks_failover_used_true_on_failover(mock_ecs_provider, mock_replicate_provider, sample_prompt, sample_style_spec):
    """Test that metadata shows failover_used=True when failover occurs (AC5)."""
    primary_error = RuntimeError("Connection timeout")
    fallback_video_url = "https://replicate.com/fallback.mp4"

    mock_ecs_provider.generate_scene_background.side_effect = primary_error
    mock_replicate_provider.generate_scene_background.return_value = fallback_video_url

    with patch('app.services.video_generator.ReplicateVideoProvider', return_value=mock_replicate_provider):
        gen = VideoGenerator(provider="replicate")
        gen.primary_provider = mock_ecs_provider
        gen.fallback_provider = mock_replicate_provider

        await gen.generate_scene_background(sample_prompt, sample_style_spec, 5.0)

        assert gen.provider_metadata["failover_used"] is True
        assert "Connection timeout" in gen.provider_metadata["failover_reason"]


@pytest.mark.asyncio
async def test_metadata_includes_timestamp(mock_replicate_provider, sample_prompt, sample_style_spec):
    """Test that metadata includes ISO format timestamp (AC5, AC6)."""
    video_url = "https://replicate.com/video.mp4"
    mock_replicate_provider.generate_scene_background.return_value = video_url

    with patch('app.services.video_generator.ReplicateVideoProvider', return_value=mock_replicate_provider):
        gen = VideoGenerator(provider="replicate")
        await gen.generate_scene_background(sample_prompt, sample_style_spec, 5.0)

        assert "timestamp" in gen.provider_metadata
        # Verify ISO format with Z suffix
        timestamp = gen.provider_metadata["timestamp"]
        assert timestamp.endswith("Z")
        # Verify parseable as datetime
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


# ============================================================================
# Test Logging (AC6)
# ============================================================================

@pytest.mark.asyncio
async def test_error_logged_when_primary_fails(mock_ecs_provider, mock_replicate_provider, sample_prompt, sample_style_spec, caplog):
    """Test that ERROR level log is generated when primary provider fails (AC6)."""
    primary_error = RuntimeError("Primary failed")
    fallback_video_url = "https://replicate.com/fallback.mp4"

    mock_ecs_provider.generate_scene_background.side_effect = primary_error
    mock_replicate_provider.generate_scene_background.return_value = fallback_video_url

    with patch('app.services.video_generator.ReplicateVideoProvider', return_value=mock_replicate_provider):
        gen = VideoGenerator(provider="replicate")
        gen.primary_provider = mock_ecs_provider
        gen.fallback_provider = mock_replicate_provider

        with caplog.at_level(logging.ERROR):
            await gen.generate_scene_background(sample_prompt, sample_style_spec, 5.0)

        # Verify ERROR log exists
        error_logs = [record for record in caplog.records if record.levelname == "ERROR"]
        assert len(error_logs) >= 1
        assert any("Primary provider" in record.message and "failed" in record.message for record in error_logs)


@pytest.mark.asyncio
async def test_warning_logged_when_failover_activates(mock_ecs_provider, mock_replicate_provider, sample_prompt, sample_style_spec, caplog):
    """Test that WARNING level log is generated when failover activates (AC6)."""
    primary_error = RuntimeError("Primary unavailable")
    fallback_video_url = "https://replicate.com/fallback.mp4"

    mock_ecs_provider.generate_scene_background.side_effect = primary_error
    mock_replicate_provider.generate_scene_background.return_value = fallback_video_url

    with patch('app.services.video_generator.ReplicateVideoProvider', return_value=mock_replicate_provider):
        gen = VideoGenerator(provider="replicate")
        gen.primary_provider = mock_ecs_provider
        gen.fallback_provider = mock_replicate_provider

        with caplog.at_level(logging.WARNING):
            await gen.generate_scene_background(sample_prompt, sample_style_spec, 5.0)

        # Verify WARNING logs exist for failover
        warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
        assert len(warning_logs) >= 1
        assert any("Failing over" in record.message for record in warning_logs)


@pytest.mark.asyncio
async def test_log_message_includes_failing_over_to_replicate(mock_ecs_provider, mock_replicate_provider, sample_prompt, sample_style_spec, caplog):
    """Test that failover log message includes 'Failing over to replicate...' (AC6)."""
    primary_error = RuntimeError("ECS timeout")
    fallback_video_url = "https://replicate.com/fallback.mp4"

    mock_ecs_provider.generate_scene_background.side_effect = primary_error
    mock_replicate_provider.generate_scene_background.return_value = fallback_video_url

    with patch('app.services.video_generator.ReplicateVideoProvider', return_value=mock_replicate_provider):
        gen = VideoGenerator(provider="replicate")
        gen.primary_provider = mock_ecs_provider
        gen.fallback_provider = mock_replicate_provider

        with caplog.at_level(logging.WARNING):
            await gen.generate_scene_background(sample_prompt, sample_style_spec, 5.0)

        # Verify specific failover message
        assert any("Failing over to replicate" in record.message for record in caplog.records)
