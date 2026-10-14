"""Unit tests for image generation endpoints."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, patch


def test_images_config_endpoint(make_client):
    client = make_client()
    res = client.get("/api/images/config")
    assert res.status_code == 200
    data = res.json()
    assert "engines" in data
    assert "pollinations" in data["engines"]
    assert "huggingface" in data["engines"]
    assert "default_engine" in data


@patch("app.routes.images.generate_image", new_callable=AsyncMock)
def test_images_generate_success(mock_gen: AsyncMock, make_client):
    client = make_client()
    fake_png = b"\x89PNG\r\n\x1a\nfakeimagebytes"
    mock_gen.return_value = (fake_png, "image/png", "Pollinations.ai (Flux)")

    res = client.post(
        "/api/images/generate",
        json={
            "prompt": "A cute cat on a laptop",
            "engine": "pollinations",
            "width": 512,
            "height": 512,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "image" in data
    assert data["image"]["media_type"] == "image/png"
    assert data["image"]["engine"] == "Pollinations.ai (Flux)"
    assert data["image"]["prompt"] == "A cute cat on a laptop"

    # Verify base64 content
    decoded = base64.b64decode(data["image"]["data"])
    assert decoded == fake_png


def test_images_generate_validation_empty_prompt(make_client):
    client = make_client()
    res = client.post("/api/images/generate", json={"prompt": ""})
    assert res.status_code == 422


def test_images_generate_validation_bad_size(make_client):
    client = make_client()
    res = client.post("/api/images/generate", json={"prompt": "test", "width": 50})
    assert res.status_code == 422


@patch("app.routes.images.generate_image_to_image", new_callable=AsyncMock)
def test_images_generate_img2img_success(mock_img2img: AsyncMock, make_client):
    client = make_client()
    fake_png = b"\x89PNG\r\n\x1a\nfakeimagebytes"
    mock_img2img.return_value = (fake_png, "image/png", "Pollinations.ai (Image-to-Image)")

    res = client.post(
        "/api/images/generate",
        json={
            "prompt": "turn this into an anime style portrait",
            "image": "data:image/png;base64,ZmFrZQ==",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "image" in data
    assert data["image"]["engine"] == "Pollinations.ai (Image-to-Image)"
    assert data["image"]["prompt"] == "turn this into an anime style portrait"
    mock_img2img.assert_awaited_once()
