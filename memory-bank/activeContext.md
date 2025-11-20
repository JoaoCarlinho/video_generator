# Active Context

## Current Focus
Debugging and fixing the video streaming issue where the frontend receives a 404 error when trying to play the generated video.

## Recent Changes
- Modified `backend/app/api/generation.py`:
  - Updated `stream_video` and `download_video` endpoints.
  - Changed logic to construct S3 key directly from `brand_id`, `perfume_id`, `campaign_id`, and `variation_index`.
  - Removed dependency on parsing the stored URL in `campaign_json`, which was causing issues due to recursive proxy URLs being stored/returned.
  - Validated against `s3_client.head_object` before streaming.

## Context
The issue was caused by the `get_campaign` endpoint rewriting S3 URLs to backend proxy URLs (`http://localhost:8000/.../stream/...`). When the `stream_video` endpoint received a request, it tried to parse this proxy URL as an S3 URL and failed. By constructing the S3 key directly based on the known hierarchy (`brands/{brand_id}/perfumes/{perfume_id}/campaigns/{campaign_id}/variation_{i}/final/final_video.mp4`), we bypass this issue entirely.

## Next Steps
- Verify that video playback works correctly in the frontend.
- Ensure other aspect ratios (if added later) are handled correctly (currently only 9:16 is supported).
