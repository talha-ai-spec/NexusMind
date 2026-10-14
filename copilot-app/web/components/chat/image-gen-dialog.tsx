"use client";

import { Loader2Icon, SparklesIcon, Wand2Icon } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { generateImage } from "@/lib/api";
import { VERIFIED_IMAGE_MODELS, type GeneratedImage, type ImageModelOption } from "@/lib/types";

export interface ImageGenDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: (image: GeneratedImage, prompt: string) => void;
  initialPrompt?: string;
}

const ASPECT_RATIOS = [
  { label: "Square (1:1)", width: 1024, height: 1024 },
  { label: "Landscape (16:9)", width: 1280, height: 720 },
  { label: "Portrait (9:16)", width: 720, height: 1280 },
];

export function ImageGenDialog({
  open,
  onOpenChange,
  onSuccess,
  initialPrompt = "",
}: ImageGenDialogProps) {
  const [prompt, setPrompt] = useState(initialPrompt);
  const [selectedModel, setSelectedModel] = useState<ImageModelOption>(VERIFIED_IMAGE_MODELS[0]);
  const [ratioIndex, setRatioIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    const text = prompt.trim();
    if (!text) return;

    setLoading(true);
    setError(null);

    const ratio = ASPECT_RATIOS[ratioIndex];

    try {
      const generated = await generateImage({
        prompt: text,
        engine: selectedModel.engine,
        model: selectedModel.model,
        width: ratio.width,
        height: ratio.height,
      });

      onSuccess(generated, text);
      onOpenChange(false);
      setPrompt("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate image");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <SparklesIcon className="h-5 w-5 text-amber-500" />
            Generate Image
          </DialogTitle>
          <DialogDescription>
            Create pictures using free cloud models. Runs with zero local GPU load.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Prompt Input */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Prompt</label>
            <Textarea
              placeholder="A cute red panda wearing astronaut suit in space, digital art..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={3}
              className="resize-none"
              disabled={loading}
            />
          </div>

          {/* Model Selection */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Model & Engine</label>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              {VERIFIED_IMAGE_MODELS.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setSelectedModel(opt)}
                  disabled={loading}
                  className={`flex flex-col items-start rounded-lg border p-2 text-left transition ${
                    selectedModel.id === opt.id
                      ? "border-primary bg-primary/5 text-foreground ring-1 ring-primary"
                      : "border-border hover:bg-muted/50 text-muted-foreground"
                  }`}
                >
                  <span className="text-xs font-medium text-foreground">{opt.name}</span>
                  <span className="text-[10px] text-muted-foreground">{opt.badge}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Aspect Ratio */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Dimensions</label>
            <div className="flex gap-2">
              {ASPECT_RATIOS.map((item, idx) => (
                <button
                  key={item.label}
                  type="button"
                  onClick={() => setRatioIndex(idx)}
                  disabled={loading}
                  className={`flex-1 rounded-md border py-1.5 text-center text-xs transition ${
                    ratioIndex === idx
                      ? "border-primary bg-primary/10 font-medium text-primary"
                      : "border-border text-muted-foreground hover:bg-muted/50"
                  }`}
                >
                  {item.label.split(" ")[0]}
                </button>
              ))}
            </div>
          </div>

          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleGenerate} disabled={loading || !prompt.trim()} className="gap-2">
            {loading ? (
              <>
                <Loader2Icon className="h-4 w-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Wand2Icon className="h-4 w-4" />
                Generate
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
