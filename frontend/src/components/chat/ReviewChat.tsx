/**
 * ReviewChat Component (Interactive Multi-Turn RAG Chat UI & Source Context Drawer)
 *
 * Implements FE-09 (Issue #69):
 * - Grounded academic Q&A against the review's pgvector knowledge base
 * - Reliable multi-turn conversation history excluding welcome and error messages
 * - Interactive and independently expandable citation accordions displaying retrieved snippets
 * - Robust review ID isolation and race-condition protection
 * - Loading indicators, input validation, auto-scroll, and graceful error handling
 */

import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  Bot,
  User,
  ChevronDown,
  ChevronUp,
  Database,
  Sparkles,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { ChatMessage, ChatHistoryMessage, CitationSource } from "../../types";
import { sendReviewChatMessage } from "../../lib/api";

export interface ReviewChatProps {
  reviewId: string;
  className?: string;
}

const WELCOME_CONTENT =
  "Hello! I am your research assistant grounded in the literature reviewed for this session. Ask me anything about specific findings, methodologies, or comparisons across the analyzed papers.";

/**
 * Creates the initial welcome greeting message from the RAG research assistant.
 *
 * @returns A ChatMessage initialized with the default academic assistant greeting.
 */
function createWelcomeMessage(): ChatMessage {
  return {
    id: "welcome",
    role: "assistant",
    content: WELCOME_CONTENT,
    timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  };
}

/**
 * Interactive Multi-Turn RAG Chat UI & Source Context Drawer component.
 *
 * Provides a conversational assistant interface grounded in pgvector literature chunk embeddings.
 * Features strict multi-turn history serialization, expandable citation evidence drawers,
 * auto-scrolling, review ID isolation, and graceful error handling.
 */
export const ReviewChat: React.FC<ReviewChatProps> = ({ reviewId, className = "" }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([createWelcomeMessage()]);
  const [inputQuery, setInputQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const currentReviewIdRef = useRef(reviewId);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Review ID isolation: Reset conversation & abort in-flight requests when reviewId changes
  useEffect(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    currentReviewIdRef.current = reviewId;
    setMessages([createWelcomeMessage()]);
    setExpandedSources({});
    setInputQuery("");
    setIsLoading(false);

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, [reviewId]);

  /**
   * Smoothly scrolls the chat message viewport to the newest message or typing indicator.
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  /**
   * Toggles the expanded/collapsed state of the retrieved sources drawer for a specific assistant message.
   *
   * @param msgId - The unique ID of the assistant message whose citation accordion should toggle.
   */
  const toggleSources = (msgId: string) => {
    setExpandedSources((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  /**
   * Handles user question submission and orchestrates the full RAG chat request lifecycle.
   *
   * Workflow and Invariants:
   * 1. **Validation & Deduplication**:
   *    Validates that the input query is non-empty after trimming, verifies that a valid `reviewId`
   *    exists, and rejects concurrent submissions while `isLoading` is true.
   * 2. **Conversation History Serialization**:
   *    - Identifies all previously completed turns by finding turn IDs with a successful, non-error
   *      assistant response (`successfulTurnIds`).
   *    - Excludes the initial welcome greeting (`id === 'welcome'`).
   *    - Excludes prior assistant error notices (`isError === true`).
   *    - Excludes failed or unanswered user questions (whose turn did not produce a valid assistant answer).
   *    - Excludes the currently submitted question because it is transmitted separately in the `question` field.
   *    - Maps valid turns to `{ role: 'user' | 'assistant', content }` while preserving chronological order.
   * 3. **Turn Initialization & Optimistic User Message**:
   *    - Generates a unique, stable `turnId` correlating the user question with its subsequent response.
   *    - Immediately appends the user message in `status: 'pending'` and activates the loading indicator.
   *    - Clears the input field immediately to provide responsive feedback.
   * 4. **Network Request & In-Flight Abort Management**:
   *    - Creates an `AbortController` stored in `abortControllerRef` to enable request cancellation if the
   *      component unmounts or if the user switches to a different review.
   *    - Calls `sendReviewChatMessage` targeting `POST /api/v1/reviews/{reviewId}/chat` with `{ question, history }`.
   * 5. **Stale Review Protection & Race-Condition Guarding**:
   *    - Checks `currentReviewIdRef.current === activeReviewId` before applying any state updates.
   *    - Discards responses and errors if the user switched reviews while the request was in flight.
   * 6. **Response & Failure Handling**:
   *    - **On Success**: Appends the assistant message with `status: 'success'` and retrieved `citations`,
   *      while promoting the correlated user message to `status: 'success'`.
   *    - **On Error**: Ignores `AbortError` and stale review responses. For actual failures, appends an
   *      assistant error bubble with `isError: true` and `status: 'error'`, and updates the correlated
   *      user message to `status: 'error'`. This preserves visible error feedback for the user while
   *      preventing failed questions from contaminating subsequent conversation turns.
   *    - **Cleanup**: Clears the loading state (`isLoading = false`) if the review remains active.
   *
   * @param e - The form submission event.
   */
  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = inputQuery.trim();
    if (!trimmed || isLoading || !reviewId) return;

    // Build history from previous completed turns:
    // - Exclude welcome message
    // - Exclude error messages
    // - Exclude user messages whose corresponding request failed (turn without successful assistant response)
    // - Exclude current question (sent separately as `question`)
    // - Strict ChatHistoryMessage format: { role, content }
    const successfulTurnIds = new Set(
      messages
        .filter((m) => m.role === "assistant" && !m.isError && m.id !== "welcome" && m.turnId)
        .map((m) => m.turnId as string)
    );

    const historyPayload: ChatHistoryMessage[] = messages
      .filter((m) => m.id !== "welcome" && !m.isError && m.turnId && successfulTurnIds.has(m.turnId))
      .map((m) => ({
        role: m.role,
        content: m.content,
      }));

    const turnId = `turn-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    const userMessageId = `user-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    const userMsg: ChatMessage = {
      id: userMessageId,
      turnId,
      role: "user",
      content: trimmed,
      status: "pending",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery("");
    setIsLoading(true);

    const activeReviewId = reviewId;
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const res = await sendReviewChatMessage(
        activeReviewId,
        trimmed,
        historyPayload,
        controller.signal
      );

      // Verify the review ID hasn't changed while request was in-flight
      if (currentReviewIdRef.current !== activeReviewId) {
        return;
      }

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        turnId,
        role: "assistant",
        content: res.answer || "No response generated.",
        citations: res.citations || [],
        status: "success",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) =>
        prev
          .map((m): ChatMessage => (m.turnId === turnId ? { ...m, status: "success" } : m))
          .concat(assistantMsg)
      );
    } catch (err: unknown) {
      // Discard abortions or responses for stale reviews
      if (
        (err instanceof Error && err.name === "AbortError") ||
        currentReviewIdRef.current !== activeReviewId
      ) {
        return;
      }

      const errorMessage =
        err instanceof Error && err.message
          ? err.message
          : "Sorry, I encountered an error communicating with the RAG service. Please try again.";

      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        turnId,
        role: "assistant",
        content: errorMessage,
        isError: true,
        status: "error",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) =>
        prev
          .map((m): ChatMessage => (m.turnId === turnId ? { ...m, status: "error" } : m))
          .concat(errorMsg)
      );
    } finally {
      if (currentReviewIdRef.current === activeReviewId) {
        setIsLoading(false);
      }
    }
  };

  if (!reviewId) {
    return (
      <div
        className={`w-full bg-white rounded-2xl border border-neutral-200 shadow-xs flex flex-col items-center justify-center p-8 text-center text-neutral-500 text-sm ${className}`}
      >
        <Sparkles className="w-6 h-6 text-neutral-400 mb-2" />
        <p className="font-medium text-neutral-700">No Literature Review Selected</p>
        <p className="text-xs text-neutral-500 mt-1">
          Please select or complete a literature review to start chatting.
        </p>
      </div>
    );
  }

  return (
    <div
      className={`w-full bg-white rounded-2xl border border-neutral-200 shadow-xs flex flex-col h-[600px] overflow-hidden ${className}`}
    >
      {/* Chat Header */}
      <div className="p-4 border-b border-neutral-100 flex items-center justify-between bg-neutral-50/50">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-neutral-900">RAG Academic Assistant</h3>
            <p className="text-[11px] text-neutral-500">
              Grounded in 384D pgvector literature embeddings
            </p>
          </div>
        </div>
        <span
          role="status"
          className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full flex items-center gap-1.5 ${
            isLoading
              ? "bg-amber-50 text-amber-700"
              : "bg-emerald-50 text-emerald-700"
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              isLoading ? "bg-amber-500 animate-ping" : "bg-emerald-500 animate-pulse"
            }`}
          />
          {isLoading ? "Retrieving..." : "Ready"}
        </span>
      </div>

      {/* Messages Scroll View */}
      <div
        role="log"
        aria-live="polite"
        className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4"
      >
        {messages.map((msg, idx) => {
          const isUser = msg.role === "user";
          const msgKey = msg.id || `msg-${idx}`;
          const isSourceOpen = expandedSources[msgKey] ?? false;
          const isErrorMessage = msg.isError ?? false;

          return (
            <div
              key={msgKey}
              className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
            >
              {!isUser && (
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                    isErrorMessage
                      ? "bg-rose-100 text-rose-700"
                      : "bg-indigo-100 text-indigo-700"
                  }`}
                >
                  {isErrorMessage ? (
                    <AlertCircle className="w-4 h-4" />
                  ) : (
                    <Bot className="w-4 h-4" />
                  )}
                </div>
              )}

              <div className="max-w-[85%] sm:max-w-[78%] space-y-1.5">
                <div
                  role={isErrorMessage ? "alert" : undefined}
                  className={`p-3.5 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                    isUser
                      ? "bg-neutral-900 text-white rounded-tr-xs"
                      : isErrorMessage
                      ? "bg-rose-50 border border-rose-200 text-rose-900 rounded-tl-xs"
                      : "bg-neutral-100 text-neutral-900 rounded-tl-xs"
                  }`}
                >
                  <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                </div>

                {/* Citations Accordion for Assistant Messages */}
                {!isUser && msg.citations && msg.citations.length > 0 && (
                  <div className="border border-neutral-200/90 rounded-xl overflow-hidden bg-neutral-50/70 text-xs mt-2 transition-all shadow-2xs">
                    <button
                      type="button"
                      id={`accordion-btn-${msgKey}`}
                      aria-expanded={isSourceOpen}
                      aria-controls={`citations-${msgKey}`}
                      onClick={() => toggleSources(msgKey)}
                      className="w-full px-3 py-2 flex items-center justify-between text-[11px] text-neutral-700 hover:text-neutral-900 hover:bg-neutral-100/60 transition-colors font-medium cursor-pointer"
                    >
                      <span className="flex items-center gap-1.5">
                        <Database className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                        <span className="font-semibold text-neutral-800">
                          {msg.citations.length}{" "}
                          {msg.citations.length === 1 ? "Retrieved Source" : "Retrieved Sources"}
                        </span>
                      </span>
                      {isSourceOpen ? (
                        <ChevronUp className="w-3.5 h-3.5 text-neutral-500 shrink-0" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5 text-neutral-500 shrink-0" />
                      )}
                    </button>

                    {isSourceOpen && (
                      <div
                        id={`citations-${msgKey}`}
                        role="region"
                        aria-labelledby={`accordion-btn-${msgKey}`}
                        className="p-3 border-t border-neutral-200/70 space-y-2.5 max-h-64 overflow-y-auto"
                      >
                        {msg.citations.map((src: CitationSource, sIdx: number) => {
                          const displayTitle =
                            (src.title && src.title.trim()) || `Paper #${src.paper_id}`;

                          return (
                            <div
                              key={`citation-${src.paper_id}-${src.chunk_index}-${sIdx}`}
                              className="p-3 bg-white rounded-lg border border-neutral-200 text-[11px] space-y-2 shadow-2xs"
                            >
                              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1.5 pb-1 border-b border-neutral-100">
                                <span
                                  className="font-semibold text-neutral-900 truncate max-w-full sm:max-w-[280px]"
                                  title={displayTitle}
                                >
                                  {displayTitle}
                                </span>
                                <div className="flex items-center flex-wrap gap-1 text-[10px] text-neutral-600">
                                  <span className="px-1.5 py-0.5 bg-neutral-100 rounded text-neutral-700 font-mono">
                                    Paper #{src.paper_id}
                                  </span>
                                  <span
                                    className="px-1.5 py-0.5 bg-indigo-50 text-indigo-700 rounded font-medium truncate max-w-[150px]"
                                    title={src.section_name}
                                  >
                                    {src.section_name}
                                  </span>
                                  <span className="px-1.5 py-0.5 bg-neutral-100 rounded text-neutral-600 font-mono">
                                    Chunk {src.chunk_index}
                                  </span>
                                </div>
                              </div>
                              <blockquote className="text-neutral-700 font-serif leading-relaxed text-[11px] bg-neutral-50/60 p-2.5 rounded border-l-2 border-indigo-400 break-words whitespace-pre-wrap">
                                "{src.snippet}"
                              </blockquote>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                <span className="text-[10px] text-neutral-400 block px-1">
                  {msg.timestamp}
                </span>
              </div>

              {isUser && (
                <div className="w-7 h-7 rounded-full bg-neutral-800 text-white flex items-center justify-center shrink-0 mt-0.5">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          );
        })}

        {isLoading && (
          <div className="flex gap-3 justify-start">
            <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="p-3.5 bg-neutral-100 rounded-2xl rounded-tl-xs flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-neutral-400 animate-bounce" />
              <span className="w-2 h-2 rounded-full bg-neutral-400 animate-bounce [animation-delay:0.2s]" />
              <span className="w-2 h-2 rounded-full bg-neutral-400 animate-bounce [animation-delay:0.4s]" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <form
        onSubmit={handleSend}
        className="p-3 bg-white border-t border-neutral-200 flex items-center gap-2"
      >
        <input
          type="text"
          placeholder="Ask a question about the reviewed papers..."
          aria-label="Ask a question about the reviewed papers"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          readOnly={isLoading}
          disabled={!reviewId}
          className="flex-1 px-4 py-2.5 text-xs sm:text-sm bg-neutral-50 border border-neutral-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
        />
        <button
          type="submit"
          aria-label="Send message"
          disabled={!inputQuery.trim() || isLoading || !reviewId}
          className="p-2.5 bg-neutral-900 text-white rounded-xl hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors shrink-0 flex items-center justify-center"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </form>
    </div>
  );
};

export default ReviewChat;
