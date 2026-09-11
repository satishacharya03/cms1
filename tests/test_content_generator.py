import pytest
from unittest.mock import AsyncMock, patch
import httpx
from app.config import settings
from app.services.content_generator import (
    generate_content_for_record,
    _generate_fallback_content,
)


@pytest.fixture
def sample_report_metadata():
    return {
        "title": "Arctic Cryosphere Glaciological Assessment",
        "expedition_name": "Arctic Expedition 2026",
        "abstract": "Investigation of seasonal ice shelf degradation, albedo variation, and glacial melt dynamics across polar regions.",
        "doi": "10.1000/cryo.2026.001",
        "keywords": "cryosphere, glaciology, albedo, climate, polar",
        "link": "/reports/1",
    }


@pytest.fixture
def sample_dataset_metadata():
    return {
        "title": "Mariana Trench Abyssal CTD and Pressure Telemetry",
        "expedition_name": "Challenger Deep Abyssal Survey",
        "variables": "hydrostatic_pressure, temperature, salinity, dissolved_o2",
        "units": "MPa, degC, PSU, umol/kg",
        "temporal_coverage": "2026-04-01 to 2026-04-20",
        "spatial_coverage": "11.3733 N, 142.5917 E",
        "doi": "10.1000/mariana.2026.042",
        "keywords": "oceanography, abyssal, ctd, bathymetry, trenches",
        "license": "CC-BY-4.0",
        "link": "/datasets/1",
    }


@pytest.mark.asyncio
async def test_heuristic_fallback_when_api_key_is_placeholder(sample_report_metadata):
    """Test heuristic fallback generation when LLM API key is a placeholder."""
    original_key = settings.LLM_API_KEY
    try:
        settings.LLM_API_KEY = "gsk_placeholder_replace_with_your_free_key"
        result = await generate_content_for_record("report", sample_report_metadata)

        assert result is not None
        assert isinstance(result, dict)
        assert set(result.keys()) == {"web_summary", "tweet", "linkedin", "instagram"}

        # Constraint assertions
        # 1. web_summary: detailed, contains expedition and title
        assert len(result["web_summary"]) > 50
        assert "Arctic Expedition 2026" in result["web_summary"]
        assert "Arctic Cryosphere Glaciological Assessment" in result["web_summary"]

        # 2. tweet: <= 280 characters, includes link
        assert len(result["tweet"]) <= 280
        assert "/reports/1" in result["tweet"]

        # 3. linkedin: professional tone, includes link
        assert len(result["linkedin"]) > 50
        assert "/reports/1" in result["linkedin"]

        # 4. instagram: includes hashtags and link
        assert "#" in result["instagram"]
        assert "/reports/1" in result["instagram"]
    finally:
        settings.LLM_API_KEY = original_key


@pytest.mark.asyncio
async def test_mock_llm_valid_json_response(sample_report_metadata):
    """Mock HTTP client response simulating OpenAI-compatible LLM returning valid JSON."""
    original_key = settings.LLM_API_KEY
    try:
        settings.LLM_API_KEY = "gsk_live_valid_api_key_for_testing_12345"

        mock_llm_json_payload = {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"web_summary": "During the Arctic Expedition 2026, researchers finalized '
                            'the Arctic Cryosphere Glaciological Assessment focusing on seasonal ice dynamics. '
                            'The findings demonstrate notable shifts in albedo and shelf integrity.", '
                            '"tweet": "New research from Arctic Expedition 2026! Read the Arctic Cryosphere '
                            'Assessment: {link} #OpenScience #Cryosphere", '
                            '"linkedin": "We are proud to share our latest research publication on polar '
                            'glaciology from Arctic Expedition 2026. Access the full report at {link}.", '
                            '"instagram": "Field observations from the polar north are live! Explore findings '
                            'at the link in bio: {link}\\n\\n#Arctic #FieldScience #Research #Climate #Cryosphere"}'
                        )
                    }
                }
            ]
        }

        mock_response = httpx.Response(
            status_code=200,
            json=mock_llm_json_payload,
            request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await generate_content_for_record("report", sample_report_metadata)

            assert result is not None
            assert set(result.keys()) == {"web_summary", "tweet", "linkedin", "instagram"}
            assert len(result["tweet"]) <= 280
            assert "{link}" in result["tweet"]
            assert "Arctic Expedition 2026" in result["web_summary"]
            assert "#Arctic" in result["instagram"]
            assert mock_post.called
    finally:
        settings.LLM_API_KEY = original_key


@pytest.mark.asyncio
async def test_mock_llm_markdown_code_block_json(sample_report_metadata):
    """Test extracting JSON when LLM wraps output in markdown code fences."""
    original_key = settings.LLM_API_KEY
    try:
        settings.LLM_API_KEY = "gsk_test_markdown_fence_key"

        fenced_content = (
            '```json\n'
            '{\n'
            '  "web_summary": "Field scientists have completed the Arctic assessment with high precision.",\n'
            '  "tweet": "Arctic Cryosphere data is live: {link} #Science",\n'
            '  "linkedin": "Announcing new research findings from our Arctic survey. Full paper at {link}.",\n'
            '  "instagram": "Polar science updates: {link} #Science #Arctic #FieldWork #Research #Climate"\n'
            '}\n'
            '```'
        )

        mock_response = httpx.Response(
            status_code=200,
            json={"choices": [{"message": {"content": fenced_content}}]},
            request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await generate_content_for_record("report", sample_report_metadata)

            assert result is not None
            assert result["web_summary"] == "Field scientists have completed the Arctic assessment with high precision."
            assert len(result["tweet"]) <= 280
            assert result["tweet"] == "Arctic Cryosphere data is live: {link} #Science"
    finally:
        settings.LLM_API_KEY = original_key


@pytest.mark.asyncio
async def test_mock_llm_http_error_falls_back_to_heuristic(sample_report_metadata):
    """Test that HTTP 500 error from LLM triggers fallback generation safely."""
    original_key = settings.LLM_API_KEY
    try:
        settings.LLM_API_KEY = "gsk_valid_key_but_server_error"

        mock_response = httpx.Response(
            status_code=500,
            text="Internal Server Error",
            request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await generate_content_for_record("report", sample_report_metadata)

            assert result is not None
            assert set(result.keys()) == {"web_summary", "tweet", "linkedin", "instagram"}
            assert len(result["tweet"]) <= 280
    finally:
        settings.LLM_API_KEY = original_key


@pytest.mark.asyncio
async def test_mock_llm_missing_keys_falls_back_to_heuristic(sample_report_metadata):
    """Test that incomplete JSON response missing required platform keys falls back."""
    original_key = settings.LLM_API_KEY
    try:
        settings.LLM_API_KEY = "gsk_valid_key_incomplete_json"

        # Only 'web_summary' present, missing tweet, linkedin, instagram
        mock_response = httpx.Response(
            status_code=200,
            json={"choices": [{"message": {"content": '{"web_summary": "Only web summary"}'}}]},
            request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await generate_content_for_record("report", sample_report_metadata)

            # All 4 platforms must still be present from fallback
            assert result is not None
            assert set(result.keys()) == {"web_summary", "tweet", "linkedin", "instagram"}
    finally:
        settings.LLM_API_KEY = original_key


@pytest.mark.asyncio
async def test_dataset_heuristic_generation(sample_dataset_metadata):
    """Assert dataset records produce valid 4-platform output under heuristic generator."""
    result = _generate_fallback_content("dataset", sample_dataset_metadata)

    assert isinstance(result, dict)
    assert set(result.keys()) == {"web_summary", "tweet", "linkedin", "instagram"}
    assert "Mariana Trench Abyssal CTD" in result["web_summary"]
    assert len(result["tweet"]) <= 280
    assert "/datasets/1" in result["tweet"]
    assert "/datasets/1" in result["linkedin"]
    assert "#" in result["instagram"]
