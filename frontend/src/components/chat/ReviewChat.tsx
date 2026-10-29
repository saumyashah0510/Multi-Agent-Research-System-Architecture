/**
 * ReviewChat Component (RAG Q&A Assistant)
 *
 * Assignee Task (Issue FE-09):
 * - Provide interactive multi-turn chat interface grounded in the review's pgvector knowledge base
 * - Call POST /api/v1/reviews/{reviewId}/chat with user query & conversation history
 * - Render conversational message bubbles (User vs Assistant)
 * - Render expandable 'Retrieved Sources & Passages' accordion displaying source chunk evidence
 * - Provide auto-scroll to bottom on new messages and loading typing indicators
 */

import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, User, ChevronDown, ChevronUp, Database, Sparkles } from "lucide-react";
import { ChatMessage, SourceChunk } from "../../types";
import { sendReviewChatMessage } from "../../lib/api";

export interface ReviewChatProps {
  reviewId: string;
  className?: string;
}

export const ReviewChat: React.FC<ReviewChatProps> = ({ reviewId, className = "" }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hello! I am your research assistant grounded in the literature reviewed for this session. Ask me anything about specific findings, methodologies, or comparisons across the analyzed papers.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [inputQuery, setInputQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const toggleSources = (msgId: string) => {
    setExpandedSources((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || isLoading) return;

    const userText = inputQuery.trim();
    setInputQuery("");

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: userText,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      // TODO (Assignee - FE-09):
      // 1. Prepare history array formatted as [{ role: m.role, content: m.content }]
      // 2. Call sendReviewChatMessage(reviewId, userText, history)
      // 3. Extract assistant response text and retrieved sources from data
      // 4. Append assistant message to messages state
      const history = messages
        .filter((m) => m.id !== "welcome")
        .map((m) => ({ role: m.role, content: m.content }));

      const res = await sendReviewChatMessage(reviewId, userText, history);

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: res.response || "No response received.",
        sources: res.sources || [],
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        role: "assistant",
        content: "Sorry, I encountered an error communicating with the RAG service. Please try again.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className={`w-full bg-white rounded-2xl border border-neutral-200 shadow-xs flex flex-col h-[600px] overflow-hidden ${className}`}
    >
      {/* Chat Header */}
      <div className="p-4 border-b border-neutral-100 flex items-center justify-between bg-neutral-50/50">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-neutral-900">RAG Academic Assistant</h3>
            <p className="text-[11px] text-neutral-500">Grounded in 384D pgvector literature embeddings</p>
          </div>
        </div>
        <span className="text-[11px] bg-emerald-50 text-emerald-700 font-semibold px-2.5 py-0.5 rounded-full flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          Ready
        </span>
      </div>

      {/* Messages Scroll View */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
        {messages.map((msg, idx) => {
          const isUser = msg.role === "user";
          const msgKey = msg.id || `msg-${idx}`;
          const isSourceOpen = expandedSources[msgKey] ?? false;

          return (
            <div key={msgKey} className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
              {!isUser && (
                <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0 mt-0.5">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div className={`max-w-[85%] sm:max-w-[75%] space-y-1.5`}>
                <div
                  className={`p-3.5 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                    isUser
                      ? "bg-neutral-900 text-white rounded-tr-xs"
                      : "bg-neutral-100 text-neutral-900 rounded-tl-xs"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>

                {/* Sources Accordion for Assistant Messages */}
                {!isUser && msg.sources && msg.sources.length > 0 && (
                  <div className="border border-neutral-200 rounded-xl overflow-hidden bg-neutral-50/80 text-xs">
                    <button
                      onClick={() => toggleSources(msgKey)}
                      className="w-full px-3 py-1.5 flex items-center justify-between text-[11px] text-neutral-600 hover:text-neutral-900 font-medium"
                    >
                      <span className="flex items-center gap-1.5">
                        <Database className="w-3 h-3 text-indigo-500" />
                        <span>{msg.sources.length} Retrieved Source Passages</span>
                      </span>
                      {isSourceOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    </button>

                    {isSourceOpen && (
                      <div className="p-3 border-t border-neutral-200 space-y-2 max-h-48 overflow-y-auto">
                        {msg.sources.map((src: SourceChunk, sIdx: number) => (
                          <div
                            key={sIdx}
                            className="p-2 bg-white rounded-lg border border-neutral-100 text-[11px] space-y-1"
                          >
                            <div className="flex items-center justify-between font-semibold text-neutral-900">
                              <span className="truncate max-w-[200px]">{src.title}</span>
                              <span className="text-[10px] text-emerald-600">
                                Score: {(src.relevance_score * 100).toFixed(0)}%
                              </span>
                            </div>
                            <p className="text-neutral-600 italic">"{src.text}"</p>
                          </div>
                        ))}
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
      <form onSubmit={handleSend} className="p-3 bg-white border-t border-neutral-200 flex items-center gap-2">
        <input
          type="text"
          placeholder="Ask a question about the reviewed papers..."
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          disabled={isLoading}
          className="flex-1 px-4 py-2.5 text-xs sm:text-sm bg-neutral-50 border border-neutral-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!inputQuery.trim() || isLoading}
          className="p-2.5 bg-neutral-900 text-white rounded-xl hover:bg-neutral-800 disabled:opacity-40 transition-colors shrink-0"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};

export default ReviewChat;
