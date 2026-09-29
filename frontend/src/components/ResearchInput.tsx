import React, { useState, useRef, useEffect } from "react";
import { cn } from "../lib/utils";

interface DropdownOption {
  label: string;
  value: string;
}

function CustomDropdown({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: DropdownOption[];
  onChange: (val: string) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const selectedOption =
    options.find((opt) => opt.value === value) ?? options[0] ?? {
      label: value,
      value,
    };

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all cursor-pointer border select-none",
          isOpen
            ? "bg-white text-neutral-900 border-black/20 shadow-xs ring-2 ring-black/5"
            : "bg-neutral-100/90 text-neutral-700 border-neutral-200/60 hover:bg-neutral-200/70 hover:text-neutral-900"
        )}
      >
        <span className="text-neutral-500 font-normal">{label}:</span>
        <span className="font-semibold text-neutral-900">{selectedOption.label}</span>
        <svg
          className={cn("w-3 h-3 text-neutral-500 transition-transform duration-200", isOpen && "rotate-180")}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute left-0 bottom-full mb-1.5 sm:bottom-auto sm:top-full sm:mt-1.5 min-w-[120px] bg-white rounded-xl shadow-lg border border-neutral-200/80 p-1.5 z-50 animate-in fade-in zoom-in-95 duration-150">
          {options.map((option) => {
            const isSelected = option.value === value;
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => {
                  onChange(option.value);
                  setIsOpen(false);
                }}
                className={cn(
                  "w-full text-left px-3 py-2 rounded-lg text-xs transition-colors flex items-center justify-between cursor-pointer font-medium",
                  isSelected
                    ? "bg-[var(--color-accent)] text-neutral-900 font-semibold shadow-xs"
                    : "text-neutral-700 hover:bg-neutral-100/80 hover:text-neutral-900"
                )}
              >
                <span>{option.label}</span>
                {isSelected && (
                  <svg className="w-3.5 h-3.5 text-neutral-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

const paperOptions: DropdownOption[] = [
  { label: "5", value: "5" },
  { label: "7", value: "7" },
  { label: "10", value: "10" },
  { label: "15", value: "15" },
  { label: "20 (Max)", value: "20" },
];

const citationOptions: DropdownOption[] = [
  { label: "APA", value: "APA" },
  { label: "IEEE", value: "IEEE" },
  { label: "MLA", value: "MLA" },
  { label: "Harvard", value: "Harvard" },
  { label: "Chicago", value: "Chicago" },
];

export interface ResearchSearchParams {
  query: string;
  max_papers: number;
  citation_format?: string;
  attachedFile?: File | null;
  review_id?: string;
}

export interface ResearchInputProps {
  onSearch?: (params: ResearchSearchParams) => void;
  isLoading?: boolean;
}

export default function ResearchInput({
  onSearch,
  isLoading = false,
}: ResearchInputProps) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [numPapers, setNumPapers] = useState("10");
  const [citationFormat, setCitationFormat] = useState("APA");
  const [attachedFile, setAttachedFile] = useState<File | null>(null);

  const isSubmitting = isLoading || loading;

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setAttachedFile(e.target.files[0]);
    }
  };

  const handleTriggerUpload = () => {
    fileInputRef.current?.click();
  };

  const handleRemoveFile = () => {
    setAttachedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (isSubmitting) return;

    const finalQuery =
      query.trim() ||
      (attachedFile
        ? `Analysis of uploaded document: ${attachedFile.name}`
        : "Adaptive Retrieval Augmented Generation (Self-RAG)");

    if (!query.trim() && !attachedFile) {
      setQuery(finalQuery);
    }

    const parsedMaxPapers = Math.min(parseInt(numPapers, 10) || 10, 20);

    setLoading(true);
    try {
      const response = await fetch("/api/v1/reviews/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: finalQuery,
          citation_format: citationFormat,
          max_papers: parsedMaxPapers,
        }),
      });

      const data = response.ok ? await response.json() : null;

      if (onSearch) {
        onSearch({
          query: finalQuery,
          max_papers: parsedMaxPapers,
          citation_format: citationFormat,
          attachedFile,
          review_id: data?.review_id,
        });
      }
    } catch (err) {
      console.error("Error submitting review task:", err);
      if (onSearch) {
        onSearch({
          query: finalQuery,
          max_papers: parsedMaxPapers,
          citation_format: citationFormat,
          attachedFile,
        });
      }
    } finally {
      setLoading(false);
    }
  };


  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full bg-white rounded-2xl border border-neutral-200/90 shadow-[0_8px_30px_rgb(0,0,0,0.06)] p-3.5 sm:p-5 transition-all hover:shadow-[0_12px_40px_rgb(0,0,0,0.09)]"
    >
      {/* Hidden File Input for PDF/Document Upload */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        accept=".pdf,.doc,.docx,.txt"
        className="hidden"
      />

      {/* Top Research Input Field */}
      <div className="w-full">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="What do you want to research?"
          rows={2}
          className="w-full resize-none border-0 outline-none text-base sm:text-lg text-neutral-900 placeholder:text-neutral-400 bg-transparent p-1 sm:p-2 focus:ring-0 tracking-compact"
        />
      </div>

      {/* Uploaded File Badge */}
      {attachedFile && (
        <div className="mb-2 flex items-center gap-2 px-3 py-1.5 rounded-full bg-[var(--color-success-light)] border border-black/10 text-xs text-neutral-800 w-fit">
          <span className="font-semibold">📎 {attachedFile.name}</span>
          <span className="text-neutral-500">
            ({(attachedFile.size / 1024).toFixed(1)} KB)
          </span>
          <button
            type="button"
            onClick={handleRemoveFile}
            className="ml-1 text-neutral-500 hover:text-black cursor-pointer font-bold"
            title="Remove attachment"
          >
            ✕
          </button>
        </div>
      )}

      {/* Bottom Controls Bar: Paperclip + Number of Papers (capped at 20) + Up Arrow Submit */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 pt-3 border-t border-neutral-100">
        <div className="flex flex-wrap items-center gap-2 text-xs sm:text-sm">
          {/* Paperclip / Attachment Button */}
          <button
            type="button"
            onClick={handleTriggerUpload}
            title="Attach paper, PDF, or document"
            className={cn(
              "p-1.5 sm:p-2 rounded-lg transition-colors cursor-pointer flex items-center justify-center",
              attachedFile
                ? "bg-[var(--color-accent)] text-black"
                : "text-neutral-500 hover:text-neutral-800 hover:bg-neutral-100"
            )}
          >
            <svg
              className="w-4 h-4 sm:w-4.5 sm:h-4.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth="2"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
              />
            </svg>
          </button>

          {/* Number of Papers Custom Dropdown Chip (1 - 20) */}
          <CustomDropdown
            label="Number of Papers"
            value={numPapers}
            options={paperOptions}
            onChange={(val) => setNumPapers(val)}
          />

          {/* Citation Format Custom Dropdown Chip */}
          <CustomDropdown
            label="Citation"
            value={citationFormat}
            options={citationOptions}
            onChange={(val) => setCitationFormat(val)}
          />

        </div>

        {/* Circular Upward Arrow Submit Button */}
        <button
          type="button"
          onClick={() => handleSubmit()}
          disabled={isSubmitting}
          aria-label="Start Research"
          className={cn(
            "w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center text-white transition-all shadow-md shrink-0 cursor-pointer",
            "bg-[var(--color-primary-blue)] hover:bg-[var(--color-primary-blue-hover)] hover:scale-105 active:scale-95 shadow-[var(--color-primary-blue)]/30",
            isSubmitting && "opacity-75 cursor-wait"
          )}
        >
          {isSubmitting ? (
            <svg
              className="animate-spin h-4 w-4 text-white"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
              />
            </svg>
          ) : (
            <svg
              className="w-4 h-4 sm:w-5 sm:h-5 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth="2.5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 10l7-7m0 0l7 7m-7-7v18"
              />
            </svg>
          )}
        </button>
      </div>
    </form>
  );
}
