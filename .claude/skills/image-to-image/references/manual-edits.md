# Manual Edits for Adding Image-to-Image / Photo Editing

This reference document contains the exact code modifications to add image-to-image / photo restyling to a project that already has image generation installed.

---

## 1. `copilot-app/api/app/services/image_gen.py`

### Accept `image_url` in `generate_with_pollinations`:

```python
async def generate_with_pollinations(
    prompt: str,
    *,
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
    model: str = "flux",
    enhance: bool = False,
    image_url: str | None = None,
    request_timeout: float = 60.0,
) -> tuple[bytes, str]:
    ...
    if image_url:
        params.append(f"image={urllib.parse.quote(image_url, safe='')}")
```

### Add `upload_temp_image` and `generate_image_to_image`:

```python
async def upload_temp_image(image_data: str) -> str:
    """Uploads a base64 image or returns a URL so cloud inference can access it."""
    if image_data.startswith(("http://", "https://")):
        return image_data

    raw_b64 = image_data
    if "," in raw_b64 and "base64" in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]

    raw_bytes = base64.b64decode(raw_b64)

    # 1. Try uguu.se (fast, anonymous, 3h expiry)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                "https://uguu.se/upload",
                files={"files[]": ("source.jpg", raw_bytes, "image/jpeg")},
            )
            if res.status_code == 200:
                data = res.json()
                if data.get("success") and data.get("files"):
                    return data["files"][0]["url"]
    except Exception as e:
        logger.warning("uguu.se upload failed (%s), trying freeimage.host fallback", e)

    # 2. Try freeimage.host fallback
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            form = {
                "key": "6d207e02198a847aa98d0a2a901485a5",
                "action": "upload",
                "source": base64.b64encode(raw_bytes).decode("ascii"),
                "format": "json",
            }
            res = await client.post("https://freeimage.host/api/1/upload", data=form)
            if res.status_code == 200:
                data = res.json()
                if data.get("image", {}).get("url"):
                    return data["image"]["url"]
    except Exception as e:
        logger.warning("freeimage.host upload failed (%s)", e)

    raise RuntimeError("Failed to prepare source image for cloud processing.")


async def generate_image_to_image(
    prompt: str,
    image_input: str,
    *,
    engine: Literal["auto", "pollinations", "huggingface"] = "auto",
    hf_token: str | None = None,
    hf_model: str | None = None,
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
) -> tuple[bytes, str, str]:
    """Transform or edit an image using Pollinations with smart fallback."""
    source_url = await upload_temp_image(image_input)
    logger.info("Source image ready for img2img: %s", source_url)

    try:
        img_bytes, media = await generate_with_pollinations(
            prompt,
            width=width,
            height=height,
            seed=seed,
            image_url=source_url,
        )
        return img_bytes, media, "Pollinations.ai (Image-to-Image)"
    except Exception as e:
        logger.error("Pollinations img2img failed (%s)", e, exc_info=True)
        raise RuntimeError(f"Image editing failed: {e}") from e
```

---

## 2. `copilot-app/api/app/routes/images.py`

Update `ImageGenRequest` and route handler:

```python
class ImageGenRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    image: str | None = Field(default=None, description="Optional base64 encoded source image or URL")
    strength: float | None = Field(default=0.7, ge=0.0, le=1.0)
    engine: Literal["auto", "pollinations", "huggingface"] = "auto"
    model: str | None = None
    width: int = Field(default=1024, ge=256, le=2048)
    height: int = Field(default=1024, ge=256, le=2048)
    seed: int | None = None

@router.post("/generate", response_model=ImageGenResponse)
async def generate_image_endpoint(request: ImageGenRequest) -> ImageGenResponse:
    settings = get_settings()
    hf_token = settings.hf_token_str
    hf_model = request.model or settings.default_hf_image_model or DEFAULT_HF_MODEL

    try:
        if request.image:
            raw_bytes, media_type, engine_used = await generate_image_to_image(
                request.prompt,
                request.image,
                engine=request.engine,
                hf_token=hf_token,
                hf_model=hf_model,
                width=request.width,
                height=request.height,
                seed=request.seed,
            )
        else:
            ...
```

---

## 3. `copilot-app/web/lib/helpers.ts`

Add regex patterns for photo editing in `detectImagePrompt`:

```typescript
// Pattern E: turn/transform/convert/restyle/change/edit this (photo|picture|image)? (into|to|as|like)? (.*)
/^(?:turn|transform|convert|restyle|change|edit)\s+(?:this|the)?\s*(?:picture|image|photo)?\s*(?:into|to|as|like)?\s*(.+)$/i,
// Pattern F: make this (photo|picture|image)? (look like|into|a)? (.*)
/^(?:make)\s+(?:this|the)?\s*(?:picture|image|photo)?\s*(?:look\s+like|into|a)?\s*(.+)$/i,
```

---

## 4. `copilot-app/web/lib/api.ts`

Add `image?: string` to `GenerateImageParams`:

```typescript
export interface GenerateImageParams {
  prompt: string;
  image?: string;
  engine?: "auto" | "pollinations" | "huggingface";
  model?: string;
  width?: number;
  height?: number;
  seed?: number;
}
```

---

## 5. `copilot-app/web/hooks/use-chat.ts`

Import image loaders and extract base64 during `send` and `regenerate`:

```typescript
import { loadImage } from "@/lib/image-store";
import { blobToBase64 } from "@/lib/images";

// Inside send():
const prepareAndGenerate = async () => {
  let sourceBase64: string | undefined = undefined;
  if (images.length > 0) {
    const lastImg = images[images.length - 1];
    const blob = await loadImage(lastImg.id);
    if (blob) {
      const b64 = await blobToBase64(blob);
      sourceBase64 = `data:${lastImg.mediaType};base64,${b64}`;
    }
  }

  return generateImage({
    prompt: imagePrompt,
    image: sourceBase64,
    engine,
    model,
  });
};

// Inside regenerate():
const prepareAndRegenerate = async () => {
  let sourceBase64: string | undefined = undefined;
  if (prevUserMsg?.images && prevUserMsg.images.length > 0) {
    const lastImg = prevUserMsg.images[prevUserMsg.images.length - 1];
    const blob = await loadImage(lastImg.id);
    if (blob) {
      const b64 = await blobToBase64(blob);
      sourceBase64 = `data:${lastImg.mediaType};base64,${b64}`;
    }
  }

  return generateImage({
    prompt,
    image: sourceBase64,
    engine,
    model,
    seed: Math.floor(Math.random() * 1000000),
  });
};
```
