# Troubleshooting Image-to-Image / Photo Editing

Common issues, error codes, and troubleshooting solutions for the Image-to-Image pipeline.

---

## 1. Message Routes to Text Vision LLM Instead of Image Editor

### Symptom:
You attached a photo and typed a message, but the text assistant replied explaining the picture rather than generating an edited image.

### Cause:
The prompt was interpreted as a vision question (e.g., *"What is in this image?"* or *"Analyze this chart"*).

### Solution:
Ensure your prompt begins with or contains clear transformative editing keywords:
* *"turn this into..."*
* *"make this look like..."*
* *"restyle this photo as..."*
* *"transform this into..."*
* *"convert this picture to..."*
* Or prefix with the slash command: `/image turn this into anime`

---

## 2. "Failed to prepare source image for cloud processing"

### Symptom:
The assistant replies with an error: *"Failed to prepare source image for cloud processing"*.

### Cause:
Both temporary relay endpoints (`uguu.se` and `freeimage.host`) failed to accept the image payload. This can happen if the machine has no outbound internet connectivity, or if an aggressive corporate firewall or VPN is blocking file upload domains.

### Solution:
1. Verify internet connectivity:
   ```bash
   curl -I https://uguu.se
   curl -I https://freeimage.host
   ```
2. If working behind a strict corporate proxy, configure standard `HTTP_PROXY` or `HTTPS_PROXY` environment variables for Python `httpx`.

---

## 3. "Free generation capacity temporarily busy" (402 or 429)

### Symptom:
Pollinations returns a burst limit code (402 or 429).

### Cause:
Pollinations.ai is experiencing a sudden worldwide traffic burst on their FLUX cluster.

### Solution:
1. The backend automatically attempts to retry with the `turbo` model.
2. If both are momentarily congested, wait 20–30 seconds and click the **Regenerate** button below the message.

---

## 4. Large Image Sizes or Memory Limits

### Symptom:
Attaching raw 24-megapixel camera photos takes a long time or fails.

### Solution:
The web frontend's photo attachment pipeline automatically resizes long edges to 2048px before storing into IndexedDB and sending to the API. If uploading manually via API, keep payloads under 10MB for optimal latency.
