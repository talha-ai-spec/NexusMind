import type {
  Citation,
  GeneratedImage,
  ModelSelection,
  ModelsResponse,
  Role,
  StreamMeta,
} from "@/lib/types";

/**
 * Requests go to `/api/*` on the same origin; `next.config.ts` rewrites them to
 * the FastAPI server (API_URL), so the browser never needs CORS.
 */
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function errorMessage(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      return String(body.detail[0].msg).replace(/^Value error, /, "");
    }
  } catch {
    /* not JSON */
  }
  if (res.status === 502 || res.status === 503 || res.status === 504 || res.status === 500) {
    return "Can't reach the AI server. Make sure the API is running.";
  }
  return `Request failed (${res.status})`;
}

export async function fetchModels(refresh = false, signal?: AbortSignal): Promise<ModelsResponse> {
  console.log(`[Copilot:Models] Fetching models list (refresh=${refresh})...`);
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/models${refresh ? "?refresh=true" : ""}`, {
      cache: "no-store",
      signal,
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    console.error("[Copilot:Models] Server unreachable:", err);
    throw new ApiError("Can't reach the AI server. Make sure the API is running.");
  }
  if (!res.ok) {
    const msg = await errorMessage(res);
    console.error(`[Copilot:Models] Request failed (${res.status}):`, msg);
    throw new ApiError(msg, res.status);
  }
  const data = (await res.json()) as ModelsResponse;
  console.log(
    `[Copilot:Models] Loaded ${data.providers.length} providers (has_local=${data.has_local_models}, default='${data.default?.name}')`
  );
  return data;
}

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
  console.log("[Copilot:Image] Submitting image generation request:", {
    prompt: params.prompt,
    engine: params.engine ?? "auto",
    model: params.model,
    is_img2img: Boolean(params.image),
  });
  const res = await fetch(`${API_BASE}/images/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    const errorText = err.detail || `Image generation failed (${res.status})`;
    console.error("[Copilot:Image] Generation failed:", errorText);
    throw new Error(errorText);
  }
  const body = (await res.json()) as { image: GeneratedImage };
  console.log(
    `[Copilot:Image] Generation succeeded: id=${body.image.id}, engine=${body.image.engine}`
  );
  return body.image;
}

export interface ApiImage {
  media_type: string;
  /** Base64 without the data: prefix. */
  data: string;
}

export interface ApiMessage {
  role: Role;
  content: string;
  images?: ApiImage[];
}

export interface RagRequest {
  collections: string[];
  files: string[];
  /** The chat the files belong to; the API ignores other chats' files. */
  chat_id?: string;
}

export interface SourcesEvent {
  cited_text: string;
  grounded: boolean;
  sources: Citation[];
}

export interface StreamChatOptions {
  messages: ApiMessage[];
  selection: ModelSelection;
  /** Search these Library collections / chat files and answer with citations. */
  rag?: RagRequest | null;
  signal: AbortSignal;
  onMeta: (meta: StreamMeta) => void;
  onDelta: (text: string) => void;
  onSources?: (sources: SourcesEvent) => void;
}

/** POST /api/chat and parse the server-sent event stream. */
export async function streamChat({
  messages,
  selection,
  rag,
  signal,
  onMeta,
  onDelta,
  onSources,
}: StreamChatOptions): Promise<void> {
  const modelTag = selection ? `${selection.provider}::${selection.model}` : "auto";
  console.log(`[Copilot:Chat] Connecting SSE stream for ${messages.length} messages (target: ${modelTag})...`);
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({
        messages,
        provider: selection?.provider ?? null,
        model: selection?.model ?? null,
        ...(rag && (rag.collections.length || rag.files.length) ? { rag } : {}),
      }),
      signal,
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") {
      console.log("[Copilot:Chat] Stream aborted by client");
      throw err;
    }
    console.error("[Copilot:Chat] Connection failed:", err);
    throw new ApiError("Can't reach the AI server. Make sure the API is running.");
  }
  const reqId = res.headers.get("x-request-id");
  if (reqId) {
    console.log(`[Copilot:Chat] Stream connected (Server Request ID: ${reqId})`);
  }
  if (!res.ok) {
    const errorText = await errorMessage(res);
    console.error(`[Copilot:Chat] Stream HTTP error ${res.status}:`, errorText);
    throw new ApiError(errorText, res.status);
  }
  if (!res.body) throw new ApiError("The server returned an empty response.");

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  let finished = false;
  let chunkCount = 0;

  const handle = (block: string) => {
    let event = "message";
    const data: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
    }
    if (!data.length) return;
    const payload = JSON.parse(data.join("\n")) as Record<string, unknown>;
    switch (event) {
      case "meta":
        console.log("[Copilot:Chat] Meta event received:", payload);
        onMeta(payload as unknown as StreamMeta);
        break;
      case "sources":
        console.log("[Copilot:Chat] Sources event received:", (payload.sources as unknown[])?.length, "citations");
        onSources?.(payload as unknown as SourcesEvent);
        break;
      case "error":
        console.error("[Copilot:Chat] Error event received:", payload.message);
        throw new ApiError(String(payload.message ?? "Something went wrong."));
      case "done":
        console.log(`[Copilot:Chat] Done event received (${chunkCount} text deltas)`);
        finished = true;
        break;
      default:
        if (typeof payload.delta === "string") {
          chunkCount++;
          onDelta(payload.delta);
        }
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value.replace(/\r\n/g, "\n");
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      handle(block);
    }
  }
  if (buffer.trim()) handle(buffer);
  if (!finished) throw new ApiError("The connection closed before the reply finished.");
}
