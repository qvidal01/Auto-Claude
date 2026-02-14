"use client";

/**
 * ImageUpload - Image attachment component for tasks
 *
 * Allows users to upload images to attach to tasks or specs.
 * Supports drag-and-drop and click-to-browse.
 */

import { useCallback, useRef, useState } from "react";
import { ImagePlus, X, Upload } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui/utils";
import { Button } from "@auto-claude/ui/primitives/button";

interface ImageFile {
  id: string;
  file: File;
  preview: string;
}

interface ImageUploadProps {
  /** Called when images change */
  onChange?: (files: File[]) => void;
  /** Maximum number of images */
  maxImages?: number;
  /** Accepted file types */
  accept?: string;
  className?: string;
}

export function ImageUpload({
  onChange,
  maxImages = 5,
  accept = "image/*",
  className,
}: ImageUploadProps) {
  const { t } = useTranslation("common");
  const inputRef = useRef<HTMLInputElement>(null);
  const [images, setImages] = useState<ImageFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);

  const addFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList) return;

      const newImages: ImageFile[] = [];
      const remaining = maxImages - images.length;

      for (let i = 0; i < Math.min(fileList.length, remaining); i++) {
        const file = fileList[i];
        if (!file.type.startsWith("image/")) continue;

        newImages.push({
          id: `${Date.now()}-${i}`,
          file,
          preview: URL.createObjectURL(file),
        });
      }

      const updated = [...images, ...newImages];
      setImages(updated);
      onChange?.(updated.map((img) => img.file));
    },
    [images, maxImages, onChange],
  );

  const removeImage = useCallback(
    (id: string) => {
      const updated = images.filter((img) => {
        if (img.id === id) {
          URL.revokeObjectURL(img.preview);
          return false;
        }
        return true;
      });
      setImages(updated);
      onChange?.(updated.map((img) => img.file));
    },
    [images, onChange],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      addFiles(e.dataTransfer.files);
    },
    [addFiles],
  );

  const canAddMore = images.length < maxImages;

  return (
    <div className={cn("space-y-2", className)}>
      {/* Image previews */}
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {images.map((img) => (
            <div key={img.id} className="group relative h-16 w-16 overflow-hidden rounded-md border border-border">
              <img
                src={img.preview}
                alt=""
                className="h-full w-full object-cover"
              />
              <button
                type="button"
                onClick={() => removeImage(img.id)}
                className="absolute right-0 top-0 rounded-bl-md bg-black/60 p-0.5 opacity-0 transition-opacity group-hover:opacity-100"
              >
                <X className="h-3 w-3 text-white" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Upload area */}
      {canAddMore && (
        <div
          className={cn(
            "flex cursor-pointer flex-col items-center gap-1 rounded-lg border-2 border-dashed p-4 transition-colors",
            isDragOver
              ? "border-primary bg-primary/5"
              : "border-border hover:border-primary/50 hover:bg-accent/30",
          )}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              inputRef.current?.click();
            }
          }}
        >
          <Upload className="h-5 w-5 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">
            {t("labels.dropOrBrowse", "Drop images here or click to browse")}
          </span>
          <input
            ref={inputRef}
            type="file"
            accept={accept}
            multiple
            className="hidden"
            onChange={(e) => addFiles(e.target.files)}
          />
        </div>
      )}
    </div>
  );
}
