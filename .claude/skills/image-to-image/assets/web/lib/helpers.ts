export const uid = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2) + Date.now().toString(36);

export function makeTitle(text: string): string {
  const clean = text.replace(/\s+/g, " ").trim();
  if (!clean) return "New chat";
  return clean.length > 60 ? `${clean.slice(0, 57)}…` : clean;
}

export function formatBytes(bytes?: number | null): string {
  if (!bytes) return "";
  const gb = bytes / 1024 ** 3;
  return gb >= 1 ? `${gb.toFixed(1)} GB` : `${Math.round(bytes / 1024 ** 2)} MB`;
}

export function readStorage<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function writeStorage(key: string, value: unknown) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage full or unavailable: keep state in memory */
  }
}

/**
 * Detects if a user message is asking to generate an image.
 * Supports slash commands (/image, /imagine, /draw) and natural language
 * requests like "generate a picture of...", "draw a...", "create an image of...", etc.
 * Returns the extracted visual prompt, or null if it's an ordinary chat message.
 */
export function detectImagePrompt(text: string): string | null {
  const trimmed = text.trim();
  if (!trimmed) return null;

  // 1. Slash commands: /image, /imagine, /img, /draw
  const slashMatch = trimmed.match(/^\/(?:image|imagine|img|draw)\s+(.+)$/i);
  if (slashMatch) return slashMatch[1].trim();

  // Strip polite conversational prefixes
  const prefixRegex =
    /^(?:can\s+you\s+(?:please\s+)?|could\s+you\s+(?:please\s+)?|please\s+|i\s+want\s+(?:you\s+to\s+)?|i\s+would\s+like\s+(?:you\s+to\s+)?|i\s+need\s+(?:you\s+to\s+)?)/i;
  const stripped = trimmed.replace(prefixRegex, "").trim();

  const patterns = [
    // Pattern A: generate/create/make/render/produce (me)? (a/an/this/the)? (picture|image|photo|drawing|illustration|artwork|portrait|wallpaper) (of|showing|with|for|depicting|about|:) (.*)
    /^(?:generate|create|make|render|produce)\s+(?:me\s+)?(?:an?|the|this)?\s*(?:picture|image|photo|drawing|illustration|artwork|portrait|wallpaper)\s*(?:of|showing|with|for|depicting|about|:)\s*(.+)$/i,
    // Pattern B: draw/paint/sketch (me)? (a/an/the)? (picture|image|photo)? (of)? (.*)
    /^(?:draw|paint|sketch)\s+(?:me\s+)?(?:an?|the)?\s*(?:picture|image|photo|drawing|illustration|artwork)?\s*(?:of|showing|with|for|depicting)?\s*(.+)$/i,
    // Pattern C: show me (a/an/the)? (picture|image|photo) (of/showing/with) (.*)
    /^(?:show\s+me)\s+(?:an?|the)?\s*(?:picture|image|photo)\s+(?:of|showing|with|depicting)\s+(.+)$/i,
    // Pattern D: generate/create this picture: (.*)
    /^(?:generate|create|render)\s+(?:this|the)?\s*(?:picture|image|photo)\s*:\s*(.+)$/i,
    // Pattern E: turn/transform/convert/restyle/change/edit this (photo|picture|image)? (into|to|as|like)? (.*)
    /^(?:turn|transform|convert|restyle|change|edit)\s+(?:this|the)?\s*(?:picture|image|photo)?\s*(?:into|to|as|like)?\s*(.+)$/i,
    // Pattern F: make this (photo|picture|image)? (look like|into|a)? (.*)
    /^(?:make)\s+(?:this|the)?\s*(?:picture|image|photo)?\s*(?:look\s+like|into|a)?\s*(.+)$/i,
  ];

  for (const pat of patterns) {
    const m = stripped.match(pat);
    if (m && m[1]?.trim()) {
      let candidate = m[1].trim().replace(/[\?\.\!]+$/, "").trim();
      candidate = candidate.replace(/^(?:this:\s*|this\s+)/i, "").trim();
      // Strip leading punctuation like commas, colons, hyphens
      candidate = candidate.replace(/^[\s,:\-]+/, "").trim();
      // Strip leading helper prepositions/conjunctions
      candidate = candidate.replace(/^(?:to\s+|and\s+|so\s+that\s+it\s+is\s+)/i, "").trim();

      // Guard against false positives:
      // 1. Non-visual language like "draw conclusions"
      if (candidate.toLowerCase().startsWith("conclusion")) {
        return null;
      }

      // 2. Guard against troubleshooting / bug / code error questions
      // These must be sent to the Vision LLM (e.g. Gemini) so the AI can analyze the screenshot!
      const lowerCandidate = candidate.toLowerCase();
      const isTroubleshooting =
        lowerCandidate.includes("error") ||
        lowerCandidate.includes("bug") ||
        lowerCandidate.includes("issue") ||
        lowerCandidate.includes("warning") ||
        lowerCandidate.includes("exception") ||
        lowerCandidate.includes("problem") ||
        lowerCandidate.includes("fix") ||
        lowerCandidate.includes("solve") ||
        lowerCandidate.includes("debug") ||
        lowerCandidate.includes("why is") ||
        lowerCandidate.includes("what is") ||
        lowerCandidate.includes("explain") ||
        lowerCandidate.includes("describe");

      if (isTroubleshooting) {
        return null;
      }

      if (candidate) return candidate;
    }
  }

  return null;
}

