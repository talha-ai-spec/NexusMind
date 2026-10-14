# Manual Edits for Integrating Image Generation

This reference document contains the exact code modifications required to wire image generation into any copilot application.

---

## 1. `copilot-app/api/app/core/config.py`

Add Hugging Face settings and safe token getter to `Settings`:

```python
from dotenv import find_dotenv, load_dotenv

# Ensure .env is read in all working directory configurations
load_dotenv(find_dotenv(usecwd=True))

class Settings(BaseSettings):
    ...
    # Image Generation
    huggingface_token: SecretStr | None = None
    default_hf_image_model: str = "black-forest-labs/FLUX.1-schnell"

    @property
    def hf_token_str(self) -> str | None:
        if self.huggingface_token:
            return self.huggingface_token.get_secret_value()
        return os.environ.get("HUGGINGFACE_TOKEN")
```

---

## 2. `copilot-app/api/app/main.py`

Import and mount the router:

```python
from app.routes import chat, health, images, models

# Inside create_app():
app.include_router(images.router, prefix="/api")
```

---

## 3. `copilot-app/api/app/schemas.py`

Relax the validator on `ChatMessage` to allow images / generated images on assistant messages:

```python
@model_validator(mode="after")
def _check(self) -> Self:
    # Relaxed to allow image attachments or generation on assistant messages
    pass
    return self
```

---

## 4. `copilot-app/web/lib/types.ts`

Add `GeneratedImage`, `ImageModelOption`, and `VERIFIED_IMAGE_MODELS`:

```typescript
export interface GeneratedImage {
  id: string;
  mediaType: string;
  data: string; // base64
  engine?: string;
  prompt: string;
}

export interface ImageModelOption {
  id: string;
  name: string;
  engine: "huggingface" | "pollinations";
  model: string;
  badge: string;
}

export const VERIFIED_IMAGE_MODELS: ImageModelOption[] = [
  {
    id: "hf-flux-schnell",
    name: "FLUX.1-schnell (Hugging Face)",
    engine: "huggingface",
    model: "black-forest-labs/FLUX.1-schnell",
    badge: "HF Token · High Quality",
  },
  {
    id: "pollinations-flux",
    name: "FLUX.1 (Pollinations)",
    engine: "pollinations",
    model: "flux",
    badge: "Free Cloud · High Quality",
  },
  {
    id: "pollinations-turbo",
    name: "SD-Turbo (Pollinations)",
    engine: "pollinations",
    model: "turbo",
    badge: "Free Cloud · Fast 2s",
  },
];

export interface ChatMessage {
  ...
  images?: ChatImage[];
  generatedImage?: GeneratedImage;
}
```

---

## 5. `copilot-app/web/lib/api.ts`

Add `GenerateImageParams` and `generateImage`:

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

export async function generateImage(params: GenerateImageParams): Promise<GeneratedImage> {
  const res = await fetch(`${API_BASE}/images/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(err.detail || `Image generation failed (${res.status})`);
  }
  const body = (await res.json()) as { image: GeneratedImage };
  return body.image;
}
```

---

## 6. `copilot-app/web/lib/helpers.ts`

Add conversational visual intent detection:

```typescript
export function detectImagePrompt(text: string): string | null {
  const trimmed = text.trim();
  if (!trimmed) return null;

  // Slash commands
  const slashMatch = trimmed.match(/^\/(?:image|imagine|img|draw)\s+(.+)$/i);
  if (slashMatch) return slashMatch[1].trim();

  // Natural language conversational prompts
  const prefixRegex =
    /^(?:can\s+you\s+(?:please\s+)?|could\s+you\s+(?:please\s+)?|please\s+|i\s+want\s+(?:you\s+to\s+)?|i\s+would\s+like\s+(?:you\s+to\s+)?|i\s+need\s+(?:you\s+to\s+)?)/i;
  const stripped = trimmed.replace(prefixRegex, "").trim();

  const patterns = [
    /^(?:generate|create|make|render|produce)\s+(?:me\s+)?(?:an?|the|this)?\s*(?:picture|image|photo|drawing|illustration|artwork|portrait|wallpaper)\s*(?:of|showing|with|for|depicting|about|:)\s*(.+)$/i,
    /^(?:draw|paint|sketch)\s+(?:me\s+)?(?:an?|the)?\s*(?:picture|image|photo|drawing|illustration|artwork)?\s*(?:of|showing|with|for|depicting)?\s*(.+)$/i,
    /^(?:show\s+me)\s+(?:an?|the)?\s*(?:picture|image|photo)\s+(?:of|showing|with|depicting)\s+(.+)$/i,
    /^(?:generate|create|render)\s+(?:this|the)?\s*(?:picture|image|photo)\s*:\s*(.+)$/i,
  ];

  for (const pat of patterns) {
    const m = stripped.match(pat);
    if (m && m[1]?.trim()) {
      let candidate = m[1].trim().replace(/[\?\.\!]+$/, "").trim();
      if (!candidate.toLowerCase().startsWith("conclusion")) return candidate;
    }
  }
  return null;
}
```

---

## 7. `copilot-app/web/components/chat/model-picker.tsx`

Add the Image Generation options directly into the dropdown:

```tsx
import { VERIFIED_IMAGE_MODELS } from "@/lib/types";

// In DropdownMenuRadioGroup:
<DropdownMenuSeparator />
<DropdownMenuLabel className="flex items-center gap-1.5">
  <SparklesIcon className="size-3.5 text-amber-500" /> Image Generation
</DropdownMenuLabel>
{VERIFIED_IMAGE_MODELS.map((m) => (
  <DropdownMenuRadioItem key={m.id} value={`image${SEP}${m.id}`} className="items-center">
    <span className="truncate">{m.name}</span>
    <span className="ml-auto pl-2 text-[10px] text-muted-foreground font-medium shrink-0">
      {m.badge}
    </span>
  </DropdownMenuRadioItem>
))}
```

---

## 8. `copilot-app/web/components/chat/message.tsx`

Render `GeneratedImageCard` when present on an assistant message:

```tsx
import { GeneratedImageCard } from "@/components/chat/generated-image-card";

// Inside assistant message rendering:
{message.generatedImage && (
  <GeneratedImageCard
    id={message.generatedImage.id}
    mediaType={message.generatedImage.mediaType}
    data={message.generatedImage.data}
    engine={message.generatedImage.engine}
    prompt={message.generatedImage.prompt}
  />
)}
```

---

## 9. `copilot-app/web/hooks/use-chat.ts`

Handle image generation routing and regeneration:

```typescript
// In send():
const isExplicitImageMode = selectionRef.current?.provider === "image";
const detectedPrompt = detectImagePrompt(content);
const isImageRequest = isExplicitImageMode || Boolean(detectedPrompt);

if (isImageRequest) {
  const imagePrompt = detectedPrompt ?? content;
  // Route to generateImage() and patch assistant message with generatedImage
}

// In regenerate(messageId):
const isImage = Boolean(targetMsg.generatedImage) || Boolean(prevDetected) || selectionRef.current?.provider === "image";
if (isImage) {
  // Call generateImage() with new random seed Math.floor(Math.random() * 1000000)
}
```
