import { ExternalLink } from "lucide-react";

export interface ReferenceItem {
  title?: string;
  authors?: string[];
  year?: number;
  url?: string;
  matched_passage?: string;
}

export interface ReferenceCardProps {
  reference: ReferenceItem;
  index: number;
}

function formatAuthors(authors?: string[]): string {
  if (!authors || authors.length === 0) return "Authors unlisted";
  if (authors.length === 1) return authors[0] || "Authors unlisted";
  if (authors.length === 2) return `${authors[0]}, ${authors[1]}`;
  return `${authors[0]} et al.`;
}

export default function ReferenceCard({ reference, index }: ReferenceCardProps) {
  const title = reference.title || `Reference #${index + 1}`;
  const authorsText = formatAuthors(reference.authors);

  return (
    <div
      id={`reference-${index + 1}`}
      className="scroll-mt-24 bg-white rounded-xl border border-neutral-200/85 px-4 sm:px-5 py-3.5 shadow-2xs hover:border-neutral-300 transition-colors flex items-center justify-between gap-4"
    >
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-baseline gap-2">
          <span className="text-xs font-bold text-[var(--color-success-dark)] tabular-nums shrink-0">
            [{index + 1}]
          </span>
          <h4 className="font-sans text-xs sm:text-sm font-semibold text-neutral-900 leading-snug">
            {title}
          </h4>
        </div>

        <p className="font-sans text-xs text-neutral-500 pl-6">
          {authorsText}
        </p>
      </div>

      {reference.url && (
        <a
          href={reference.url}
          target="_blank"
          rel="noopener noreferrer"
          title="Open source paper in new tab"
          aria-label={`Open source link for ${title}`}
          style={{ borderRadius: "var(--radius-sm)" }}
          className="w-7 h-7 inline-flex items-center justify-center text-[var(--color-sky-dark)] hover:text-[#005fa8] bg-white hover:bg-[var(--tint-sky)] transition-colors border border-neutral-200/90 hover:border-[var(--color-pill-sky)] shrink-0 shadow-2xs"
        >
          <ExternalLink className="w-3.5 h-3.5 stroke-[2.25]" />
        </a>
      )}
    </div>
  );
}
