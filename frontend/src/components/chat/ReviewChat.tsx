/**
 * ReviewChat Component
 *
 * Implements the redesigned Scholaris Literature Review Two-Column Q&A Chat UI:
 * - Top Page Header: "Chat with your research"
 * - Left Column: Collapsible "Your chats" sidebar with + New chat, search filter, and active mint pill highlight
 * - Right Column: Main Chat Panel with review subcaption, Export chat, scrollable message feed, and pinned input
 * - Hover-Triggered Single-Source Popovers on citation chips ([1], [2])
 * - Viewport-locked 100vh layout with scoped smooth auto-scrolling
 */

import React, { useState, useRef, useEffect, useMemo } from "react";
import {
  ArrowLeft,
  ArrowUp,
  Sparkles,
  Download,
  Check,
  Loader2,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Search,
} from "lucide-react";
import { ChatMessage, ChatHistoryMessage, CitationSource } from "../../types";
import { sendReviewChatMessage, getReviewStatus, fetchPastReviews } from "../../lib/api";
import { cn } from "../../lib/utils";
import { FiUser } from "react-icons/fi";

export interface ReviewChatProps {
  reviewId?: string;
  topic?: string;
  onSelectReviewSession?: (reviewId: string, topic?: string) => void;
  onStartNewChat?: () => void;
  onBackToPastReviews?: () => void;
  className?: string;
}

function formatCreatedDate(isoString?: string): string {
  if (!isoString) return "Recently";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return "Recently";
    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return "Recently";
  }
}

/**
 * Single-Source Citation Chip with Hover-Triggered Popover
 */
interface CitationChipProps {
  citation: CitationSource;
  index: number;
}

export const CitationChip: React.FC<CitationChipProps> = ({ citation, index }) => {
  const [isHovered, setIsHovered] = useState(false);
  const timeoutRef = useRef<number | null>(null);
  const isOverPopoverRef = useRef(false);

  const handleMouseEnter = () => {
    if (timeoutRef.current) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setIsHovered(true);
  };

  const handleMouseLeave = () => {
    timeoutRef.current = window.setTimeout(() => {
      if (!isOverPopoverRef.current) {
        setIsHovered(false);
      }
    }, 150);
  };

  const title = (citation.title && citation.title.trim()) || `Paper #${citation.paper_id}`;

  return (
    <span
      className="relative inline-block align-baseline"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <button
        type="button"
        style={{
          backgroundColor: "var(--color-success-light)",
          color: "var(--color-success-text)",
          borderRadius: "var(--radius-sm)",
          fontFamily: "var(--font-sans)",
        }}
        className="inline-flex items-center px-1.5 py-0.5 text-xs font-semibold cursor-pointer hover:opacity-85 transition-opacity select-none leading-none mx-0.5"
        aria-label={`Inspect citation [${index}]: ${title}`}
      >
        [{index}]
      </button>

      {/* Floating Single-Source Popover */}
      {isHovered && (
        <div
          onMouseEnter={() => {
            isOverPopoverRef.current = true;
          }}
          onMouseLeave={() => {
            isOverPopoverRef.current = false;
            setIsHovered(false);
          }}
          style={{
            backgroundColor: "var(--surface-card)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-container)",
          }}
          className="absolute bottom-full left-0 mb-2 w-72 sm:w-80 p-3 z-50 animate-in fade-in zoom-in-95 duration-150 text-left select-none pointer-events-auto"
        >
          {/* Header with index & title */}
          <div className="flex items-start gap-1.5 pb-2 mb-2 border-b border-[var(--border-subtle)]">
            <span
              style={{
                backgroundColor: "var(--color-success-light)",
                color: "var(--color-success-text)",
                borderRadius: "var(--radius-sm)",
              }}
              className="px-1.5 py-0.5 font-mono text-[11px] font-bold shrink-0 mt-0.5"
            >
              [{index}]
            </span>
            <div className="flex-1 min-w-0">
              <h4
                style={{ color: "var(--text-primary)" }}
                className="font-sans font-semibold text-xs leading-snug line-clamp-2"
              >
                {title}
              </h4>
              <div className="flex items-center gap-2 mt-0.5 text-[11px] text-[var(--text-secondary)]">
                <span>Paper #{citation.paper_id}</span>
                {citation.section_name && <span>· {citation.section_name}</span>}
              </div>
            </div>
          </div>

          {/* Excerpt Snippet */}
          {citation.snippet && (
            <p className="text-[11px] font-serif text-neutral-700 italic bg-[var(--surface-muted)] p-2 rounded border-l-2 border-[var(--color-success)] leading-relaxed line-clamp-4">
              &ldquo;{citation.snippet}&rdquo;
            </p>
          )}
        </div>
      )}
    </span>
  );
};

const TABLET_BREAKPOINT_QUERY = "(max-width: 768px)";

export const ReviewChat: React.FC<ReviewChatProps> = ({
  reviewId,
  topic,
  onSelectReviewSession,
  onStartNewChat,
  onBackToPastReviews,
  className = "",
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [copiedExport, setCopiedExport] = useState(false);
  const [resolvedTopic, setResolvedTopic] = useState<string>(topic || "");

  // Responsive mobile / tablet detection & sidebar collapse state
  const [isMobile, setIsMobile] = useState<boolean>(() => {
    if (typeof window !== "undefined" && window.matchMedia) {
      return window.matchMedia(TABLET_BREAKPOINT_QUERY).matches;
    }
    return false;
  });

  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(() => {
    if (typeof window !== "undefined" && window.matchMedia) {
      return window.matchMedia(TABLET_BREAKPOINT_QUERY).matches;
    }
    return false;
  });

  const userManuallyClosedDesktopRef = useRef<boolean>(false);
  const [sidebarSearch, setSidebarSearch] = useState("");
  const [sessions, setSessions] = useState<any[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);

  // Auto-collapse sidebar on smaller screens and restore on desktop (unless manually closed)
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;

    const mql = window.matchMedia(TABLET_BREAKPOINT_QUERY);

    const handleMediaChange = (e: MediaQueryListEvent | MediaQueryList) => {
      const matches = e.matches;
      setIsMobile(matches);
      if (matches) {
        setIsSidebarCollapsed(true);
      } else {
        if (!userManuallyClosedDesktopRef.current) {
          setIsSidebarCollapsed(false);
        }
      }
    };

    handleMediaChange(mql);

    try {
      mql.addEventListener("change", handleMediaChange);
    } catch {
      mql.addListener(handleMediaChange);
    }

    return () => {
      try {
        mql.removeEventListener("change", handleMediaChange);
      } catch {
        mql.removeListener(handleMediaChange);
      }
    };
  }, []);

  const messagesContainerRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Load past chat sessions for sidebar
  useEffect(() => {
    let isMounted = true;
    setIsLoadingSessions(true);
    fetchPastReviews(20)
      .then((data) => {
        if (!isMounted) return;
        const list = Array.isArray(data)
          ? data.map((item: any) => ({
              ...item,
              id: String(item.id),
              query: item.query || item.user_query || "Untitled Literature Review",
            }))
          : [];
        setSessions(list);
      })
      .catch((err) => {
        console.warn("Could not load past review sessions:", err);
      })
      .finally(() => {
        if (isMounted) setIsLoadingSessions(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Filtered sidebar sessions
  const filteredSessions = useMemo(() => {
    const q = sidebarSearch.trim().toLowerCase();
    if (!q) return sessions;
    return sessions.filter((s) => (s.query || "").toLowerCase().includes(q));
  }, [sessions, sidebarSearch]);

  // Sync topic prop or fetch from review status if not provided
  useEffect(() => {
    if (topic) {
      setResolvedTopic(topic);
    } else if (reviewId) {
      let isMounted = true;
      getReviewStatus(reviewId)
        .then((res) => {
          if (isMounted && res?.user_query) {
            setResolvedTopic(res.user_query);
          }
        })
        .catch(() => {});
      return () => {
        isMounted = false;
      };
    }
  }, [reviewId, topic]);

  // Load message history from session storage for this reviewId
  useEffect(() => {
    if (!reviewId) {
      setMessages([]);
      return;
    }
    try {
      const stored = sessionStorage.getItem(`scholaris_chat_${reviewId}`);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          setMessages(parsed);
          return;
        }
      }
    } catch {
      // sessionStorage error ignored
    }
    setMessages([]);
  }, [reviewId]);

  // Smooth scoped auto-scroll strictly inside messagesContainerRef
  const scrollToBottom = (smooth = true) => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: messagesContainerRef.current.scrollHeight,
        behavior: smooth ? "smooth" : "auto",
      });
    }
  };

  useEffect(() => {
    scrollToBottom(true);
  }, [messages.length, isLoading]);

  const handleExportChat = () => {
    if (messages.length === 0) return;
    const titleText = resolvedTopic || (reviewId ? `Review #${reviewId}` : "Literature Review");
    let md = `# ${titleText}\n`;
    md += `*Review ID: ${reviewId || "N/A"} | Date: ${new Date().toLocaleDateString()}*\n\n---\n\n`;

    messages.forEach((m) => {
      const sender = m.role === "user" ? "You" : "Scholaris Assistant";
      md += `### ${sender} (${m.timestamp || ""})\n\n${m.content}\n\n`;
      if (m.citations && m.citations.length > 0) {
        md += `#### Sources & Citations:\n`;
        m.citations.forEach((c, idx) => {
          md += `- [${idx + 1}] **${c.title || `Paper #${c.paper_id}`}** (${c.section_name}): "${c.snippet}"\n`;
        });
        md += `\n`;
      }
    });

    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const filename = `${titleText.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-chat.md`;
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(md).catch(() => {});
    }
    setCopiedExport(true);
    window.setTimeout(() => setCopiedExport(false), 2000);
  };

  const handleSend = async (questionText?: string) => {
    const trimmed = (questionText ?? inputQuery).trim();
    if (!trimmed || isLoading || !reviewId) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const turnId = `turn-${Date.now()}`;
    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      turnId,
      role: "user",
      content: trimmed,
      status: "pending",
      timestamp: timeStr,
    };

    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInputQuery("");
    setIsLoading(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    // Build history payload for backend RAG
    const successfulTurnIds = new Set(
      messages
        .filter((m) => m.role === "assistant" && !m.isError && m.turnId)
        .map((m) => m.turnId as string)
    );
    const historyPayload: ChatHistoryMessage[] = messages
      .filter((m) => !m.isError && m.turnId && successfulTurnIds.has(m.turnId))
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      const res = await sendReviewChatMessage(reviewId, trimmed, historyPayload, controller.signal);
      const assistantMsg: ChatMessage = {
        id: `a-${Date.now()}`,
        turnId,
        role: "assistant",
        content: res.answer || "No response generated.",
        citations: res.citations || [],
        status: "success",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => {
        const finalized = prev.map((m) =>
          m.turnId === turnId ? { ...m, status: "success" as const } : m
        );
        const newHistory = [...finalized, assistantMsg];
        try {
          sessionStorage.setItem(`scholaris_chat_${reviewId}`, JSON.stringify(newHistory));
        } catch {
          // ignored
        }
        return newHistory;
      });
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") return;

      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        turnId,
        role: "assistant",
        content:
          err instanceof Error && err.message
            ? err.message
            : "I encountered an issue retrieving grounded evidence from the knowledge base. Please try again.",
        isError: true,
        status: "error",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => {
        const finalized = prev.map((m) =>
          m.turnId === turnId ? { ...m, status: "error" as const } : m
        );
        const newHistory = [...finalized, errorMsg];
        try {
          sessionStorage.setItem(`scholaris_chat_${reviewId}`, JSON.stringify(newHistory));
        } catch {
          // ignored
        }
        return newHistory;
      });
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Helper to parse and render formatted text, splitting headings and bullet points
   * with inline hover citation chip support.
   */
  const renderFormattedBody = (content: string, citations: CitationSource[] = []) => {
    const lines = content.split("\n");
    return lines.map((line, i) => {
      const trimmed = line.trim();
      if (!trimmed) {
        return <div key={`empty-${i}`} className="h-1" />;
      }

      if (trimmed.startsWith("### ")) {
        return (
          <h4
            key={`h4-${i}`}
            style={{ fontFamily: "var(--font-serif)" }}
            className="font-bold text-xs sm:text-sm text-neutral-900 mt-3 mb-1.5"
          >
            {trimmed.replace(/^###\s+/, "")}
          </h4>
        );
      }

      if (trimmed.startsWith("• ") || trimmed.startsWith("- ")) {
        const itemText = trimmed.replace(/^[•-]\s+/, "");
        const parts = itemText.split(/(\*\*.*?\*\*|\[\d+\])/g);
        return (
          <div
            key={`li-${i}`}
            className="flex items-start gap-1.5 text-xs sm:text-sm text-neutral-800 leading-relaxed mb-1.5"
          >
            <span className="text-neutral-900 select-none font-bold">•</span>
            <div className="flex-1">
              {parts.map((p, pIdx) => {
                if (p.startsWith("**") && p.endsWith("**")) {
                  return (
                    <strong key={pIdx} className="font-bold text-neutral-900">
                      {p.slice(2, -2)}
                    </strong>
                  );
                }
                const match = p.match(/^\[(\d+)\]$/);
                if (match && match[1]) {
                  const citationIndex = parseInt(match[1], 10);
                  const citationObj = citations[citationIndex - 1];
                  if (citationObj) {
                    return (
                      <CitationChip
                        key={pIdx}
                        citation={citationObj}
                        index={citationIndex}
                      />
                    );
                  }
                }
                return <span key={pIdx}>{p}</span>;
              })}
            </div>
          </div>
        );
      }

      const parts = trimmed.split(/(\*\*.*?\*\*|\[\d+\])/g);
      return (
        <p key={`p-${i}`} className="text-xs sm:text-sm text-neutral-800 leading-relaxed mb-2.5">
          {parts.map((p, pIdx) => {
            if (p.startsWith("**") && p.endsWith("**")) {
              return (
                <strong key={pIdx} className="font-bold text-neutral-900">
                  {p.slice(2, -2)}
                </strong>
              );
            }
            const match = p.match(/^\[(\d+)\]$/);
            if (match && match[1]) {
              const citationIndex = parseInt(match[1], 10);
              const citationObj = citations[citationIndex - 1];
              if (citationObj) {
                return (
                  <CitationChip
                    key={pIdx}
                    citation={citationObj}
                    index={citationIndex}
                  />
                );
              }
            }
            return <span key={pIdx}>{p}</span>;
          })}
        </p>
      );
    });
  };

  return (
    <div className={cn("relative w-full h-full flex gap-3 sm:gap-4 min-h-0 overflow-hidden", className)}>
      {/* Mobile Backdrop when sidebar is expanded on small screens */}
      {isMobile && !isSidebarCollapsed && (
        <div
          className="absolute inset-0 bg-black/40 backdrop-blur-[1px] z-20 transition-opacity"
          onClick={() => setIsSidebarCollapsed(true)}
          aria-label="Close chats sidebar"
        />
      )}

      {/* 1. Left Column: Collapsible Chat History Sidebar ("Your chats") */}
      {!isSidebarCollapsed && (
        <aside
          style={{
            backgroundColor: "var(--surface-card)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-lg)",
            boxShadow: isMobile ? "var(--shadow-container)" : undefined,
          }}
          className={cn(
            "flex flex-col overflow-hidden p-3 sm:p-4 shadow-xs animate-in fade-in duration-200",
            isMobile
              ? "absolute inset-2 z-30 max-w-sm mx-auto shadow-2xl"
              : "w-72 sm:w-80 shrink-0 h-full slide-in-from-left-4"
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between gap-2 mb-3 shrink-0">
            <div className="flex items-center gap-1.5 min-w-0">
              {onBackToPastReviews && (
                <button
                  type="button"
                  onClick={() => {
                    if (isMobile) setIsSidebarCollapsed(true);
                    onBackToPastReviews();
                  }}
                  title="Back to past reviews"
                  style={{
                    backgroundColor: "var(--surface-card)",
                    borderColor: "var(--border-default)",
                    color: "var(--text-primary)",
                    borderRadius: "var(--radius-sm)",
                  }}
                  className="p-1 -ml-1 border hover:bg-[var(--surface-muted)] transition-colors cursor-pointer shrink-0"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                </button>
              )}
              <h2 className="font-sans font-semibold text-sm text-[var(--text-primary)] truncate">
                Your chats
              </h2>
            </div>
            <button
              type="button"
              onClick={() => {
                if (!isMobile) {
                  userManuallyClosedDesktopRef.current = true;
                }
                setIsSidebarCollapsed(true);
              }}
              title="Collapse sidebar"
              className="p-1 rounded-md text-neutral-400 hover:text-neutral-800 hover:bg-neutral-100 transition-colors cursor-pointer shrink-0"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>

          {/* Controls: + New chat & Search chats */}
          <div className="space-y-2 mb-3 shrink-0">
            <button
              type="button"
              onClick={() => {
                if (isMobile) setIsSidebarCollapsed(true);
                onStartNewChat?.();
              }}
              style={{ borderRadius: "var(--radius-sm)" }}
              className="w-full py-2 px-3 bg-neutral-900 hover:bg-black text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer shadow-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New chat</span>
            </button>

            <div className="relative w-full">
              <Search className="w-3.5 h-3.5 text-neutral-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                value={sidebarSearch}
                onChange={(e) => setSidebarSearch(e.target.value)}
                placeholder="Search chats"
                style={{
                  backgroundColor: "var(--surface-card)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                }}
                className="w-full pl-8 pr-3 py-1.5 text-xs text-[var(--text-primary)] placeholder:text-neutral-400 focus:outline-none focus:ring-1 focus:ring-neutral-900/15"
              />
            </div>
          </div>

          {/* Chat Sessions List */}
          <div className="flex-1 min-h-0 overflow-y-auto space-y-1.5 pr-0.5">
            {isLoadingSessions && sessions.length === 0 ? (
              <div className="flex items-center justify-center py-8 text-neutral-400 gap-2 text-xs">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--status-info)]" />
                <span>Loading chats...</span>
              </div>
            ) : filteredSessions.length === 0 ? (
              <div className="text-center py-8 text-xs text-neutral-400">
                {sidebarSearch.trim() ? "No chats found." : "No previous chats yet."}
              </div>
            ) : (
              filteredSessions.map((session) => {
                const isActive = session.id === reviewId;
                return (
                  <button
                    key={session.id}
                    type="button"
                    onClick={() => {
                      if (isMobile) setIsSidebarCollapsed(true);
                      onSelectReviewSession?.(session.id, session.query);
                    }}
                    style={{
                      backgroundColor: isActive ? "var(--tint-mint)" : "transparent",
                      border: isActive
                        ? "1px solid var(--mint-dark)"
                        : "1px solid var(--border-subtle)",
                      borderRadius: "var(--radius-md)",
                    }}
                    className={cn(
                      "w-full p-2.5 text-left transition-all cursor-pointer flex flex-col gap-1",
                      isActive
                        ? "shadow-xs"
                        : "hover:bg-[var(--surface-muted)] hover:border-neutral-300"
                    )}
                  >
                    <span
                      style={{ color: "var(--text-primary)" }}
                      className={cn(
                        "font-sans text-xs line-clamp-2 leading-snug",
                        isActive ? "font-semibold" : "font-medium"
                      )}
                    >
                      {session.query}
                    </span>
                    <div className="flex items-center justify-between text-[11px] text-[var(--text-secondary)] mt-0.5">
                      <span>{formatCreatedDate(session.created_at)}</span>
                      {typeof session.paper_count === "number" && (
                        <span className="font-mono text-[10px] px-1.5 py-0.2 bg-black/5 rounded">
                          {session.paper_count} papers
                        </span>
                      )}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </aside>
      )}

      {/* 2. Right Column: Main Chat Panel */}
      <section
        style={{
          backgroundColor: "var(--surface-card)",
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-lg)",
        }}
        className="flex-1 min-w-0 h-full flex flex-col overflow-hidden shadow-xs"
      >
        {/* Card Header */}
        <header className="px-4 sm:px-6 py-2.5 sm:py-3 border-b border-[var(--border-subtle)] flex items-center justify-between gap-3 bg-[var(--surface-card)] shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            {isSidebarCollapsed && (
              <button
                type="button"
                onClick={() => {
                  if (!isMobile) {
                    userManuallyClosedDesktopRef.current = false;
                  }
                  setIsSidebarCollapsed(false);
                }}
                title="Open chats sidebar"
                style={{
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-default)",
                  backgroundColor: "var(--surface-card)",
                  color: "var(--text-primary)",
                }}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold hover:bg-[var(--surface-muted)] transition-colors cursor-pointer mr-1 shrink-0 select-none shadow-2xs"
              >
                <PanelLeftOpen className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Your chats</span>
              </button>
            )}

            <div className="min-w-0">
              <h2 className="font-sans font-semibold text-sm sm:text-base text-[var(--text-primary)] truncate">
                Ask Questions from the Selected papers
              </h2>
            </div>
          </div>

          {/* Action: Export Chat Button */}
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={handleExportChat}
              disabled={messages.length === 0}
              style={{
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-default)",
              }}
              className="px-3 py-1.5 text-xs font-semibold bg-white hover:bg-neutral-50 text-neutral-800 transition-colors flex items-center gap-1.5 cursor-pointer shrink-0 shadow-2xs disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {copiedExport ? (
                <>
                  <Check className="w-3.5 h-3.5 text-[var(--color-success)]" />
                  <span>Exported</span>
                </>
              ) : (
                <>
                  <Download className="w-3.5 h-3.5 text-neutral-600" />
                  <span>Export chat</span>
                </>
              )}
            </button>
          </div>
        </header>

        {/* Scrollable Message Feed */}
        <div
          ref={messagesContainerRef}
          className="flex-1 min-h-0 overflow-y-auto px-4 sm:px-6 py-4 space-y-4"
        >
          {messages.length === 0 ? (
            /* Clean Academic Empty State */
            <div className="h-full flex flex-col items-center justify-center text-center p-6 max-w-md mx-auto my-auto animate-in fade-in duration-300">
              <div
                style={{
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "var(--tint-mint)",
                  color: "var(--mint-dark)",
                }}
                className="w-10 h-10 flex items-center justify-center mb-3 shadow-2xs"
              >
                <Sparkles className="w-5 h-5 stroke-[2]" />
              </div>
              <h3
                style={{ fontFamily: "var(--font-serif)" }}
                className="text-base sm:text-lg font-bold text-[var(--text-primary)] tracking-compact"
              >
                Ask questions about this research
              </h3>
              <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed max-w-sm">
                Inquire about empirical evidence, methodology comparisons, or limitations across the
                papers analyzed in this review.
              </p>
            </div>
          ) : (
            messages.map((msg, idx) => {
              const isUser = msg.role === "user";
              const msgKey = msg.id || `msg-${idx}`;
              const isErrorMessage = Boolean(msg.isError);

              if (isUser) {
                return (
                  <div key={msgKey} className="flex flex-col items-end w-full animate-in fade-in">
                    <div className="flex items-center gap-1.5 mb-1 pr-1">
                      <span className="text-[11px] text-neutral-400 font-normal">
                        You · {msg.timestamp || "Now"}
                      </span>
                      <div
                        style={{
                          backgroundColor: "var(--surface-card)",
                          border: "1px solid var(--border-default)",
                          borderRadius: "var(--radius-pill)",
                        }}
                        className="w-4 h-4 rounded-full flex items-center justify-center text-[var(--text-secondary)] shadow-2xs shrink-0"
                      >
                        <FiUser className="w-2.5 h-2.5" />
                      </div>
                    </div>
                    <div
                      style={{
                        backgroundColor: "var(--tint-sky)",
                        color: "var(--text-primary)",
                      }}
                      className="rounded-2xl rounded-tr-xs px-4 py-2.5 text-xs sm:text-sm leading-relaxed max-w-[85%] sm:max-w-xl shadow-2xs"
                    >
                      <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                    </div>
                  </div>
                );
              }

              // Assistant Response
              return (
                <div
                  key={msgKey}
                  className="flex flex-col items-start w-full max-w-2xl sm:max-w-3xl animate-in fade-in"
                >
                  {/* Main Response Box */}
                  <div
                    className={cn(
                      "w-full rounded-2xl",
                      isErrorMessage
                        ? "bg-red-50 border border-red-200 text-red-900 p-4"
                        : "bg-transparent text-[var(--text-primary)]"
                    )}
                  >
                    {/* Body Content */}
                    <div className="text-xs sm:text-sm text-[var(--text-primary)]">
                      {renderFormattedBody(msg.content, msg.citations)}
                    </div>

                    {/* Sources Row: Hover-Triggered Chips (Rendered below answer text) */}
                    {!isErrorMessage && msg.citations && msg.citations.length > 0 && (
                      <div className="mt-3 pt-2 border-t border-[var(--border-subtle)]">
                        <div className="flex items-center flex-wrap gap-1.5 text-xs text-[var(--text-secondary)] py-0.5">
                          <span className="text-xs text-[var(--text-secondary)] font-semibold">Sources</span>
                          {msg.citations.map((c, cIdx) => (
                            <CitationChip
                              key={`chip-${cIdx}`}
                              citation={c}
                              index={cIdx + 1}
                            />
                          ))}
                          <span className="text-[11px] text-[var(--text-disabled)] font-normal ml-1">
                            Hover a chip to inspect source
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Pinned Footer Input */}
        <footer className="p-3 sm:p-4 bg-[var(--surface-card)] border-t border-[var(--border-subtle)] shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            style={{
              backgroundColor: "var(--surface-muted)",
              borderRadius: "var(--radius-lg)",
              border: "1px solid var(--border-default)",
            }}
            className="flex items-center gap-2 px-3 py-1.5 focus-within:ring-2 focus-within:ring-neutral-900/15 focus-within:border-neutral-300 transition-all"
          >
            <input
              ref={inputRef}
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder="Ask a follow-up about your selected papers..."
              disabled={isLoading}
              className="w-full bg-transparent text-xs sm:text-sm text-[var(--text-primary)] placeholder:text-neutral-400 focus:outline-none py-1.5"
            />
            <button
              type="submit"
              disabled={!inputQuery.trim() || isLoading}
              style={{ borderRadius: "var(--radius-sm)" }}
              className="w-7 h-7 sm:w-8 sm:h-8 rounded bg-neutral-900 text-white flex items-center justify-center hover:bg-black transition-colors disabled:opacity-30 disabled:cursor-not-allowed shrink-0 cursor-pointer shadow-xs"
              aria-label="Send message"
            >
              {isLoading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <ArrowUp className="w-4 h-4 stroke-[2.2]" />
              )}
            </button>
          </form>
          <p className="text-[11px] font-sans text-neutral-400 text-center mt-2 select-none">
            Scholaris can make mistakes. Open the cited papers to verify important claims.
          </p>
        </footer>
      </section>
    </div>
  );
};

export default ReviewChat;
