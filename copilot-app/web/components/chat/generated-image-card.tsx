"use client";

import { DownloadIcon, EyeIcon, SparklesIcon } from "lucide-react";
import Image from "next/image";
import { useState } from "react";

import { Button } from "@/components/ui/button";

export interface GeneratedImageProps {
  id: string;
  mediaType: string;
  data: string; // base64 string
  engine?: string;
  prompt: string;
  onView?: () => void;
}

export function GeneratedImageCard({
  mediaType,
  data,
  engine = "AI Generated",
  prompt,
  onView,
}: GeneratedImageProps) {
  const [downloading, setDownloading] = useState(false);
  const dataUrl = `data:${mediaType};base64,${data}`;

  const handleDownload = () => {
    try {
      setDownloading(true);
      const link = document.createElement("a");
      link.href = dataUrl;
      const ext = mediaType.includes("png") ? "png" : "jpg";
      link.download = `generated-${Date.now()}.${ext}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="group relative my-3 max-w-md overflow-hidden rounded-xl border border-border bg-card shadow-sm transition hover:shadow-md">
      {/* Image Preview */}
      <div className="relative aspect-square w-full overflow-hidden bg-muted/40">
        <img
          src={dataUrl}
          alt={prompt}
          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
        />

        {/* Hover Action Overlay */}
        <div className="absolute inset-0 flex items-center justify-center gap-2 bg-black/40 opacity-0 backdrop-blur-[2px] transition-opacity duration-200 group-hover:opacity-100">
          {onView && (
            <Button
              size="sm"
              variant="secondary"
              className="h-8 gap-1.5 rounded-full text-xs"
              onClick={onView}
            >
              <EyeIcon className="h-3.5 w-3.5" />
              View
            </Button>
          )}
          <Button
            size="sm"
            variant="secondary"
            className="h-8 gap-1.5 rounded-full text-xs"
            onClick={handleDownload}
            disabled={downloading}
          >
            <DownloadIcon className="h-3.5 w-3.5" />
            Download
          </Button>
        </div>
      </div>

      {/* Info Footer */}
      <div className="flex items-center justify-between border-t border-border/60 bg-card/80 px-3 py-2 text-xs text-muted-foreground backdrop-blur-sm">
        <div className="flex items-center gap-1.5 truncate pr-2">
          <SparklesIcon className="h-3.5 w-3.5 shrink-0 text-amber-500" />
          <span className="truncate font-medium text-foreground">{prompt}</span>
        </div>
        <span className="shrink-0 rounded-md bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
          {engine}
        </span>
      </div>
    </div>
  );
}
