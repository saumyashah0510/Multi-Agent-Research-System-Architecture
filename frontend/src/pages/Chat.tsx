import { useState, useRef, useEffect } from "react";
import { Badge } from "../components/ui/badge";

interface Message {
  id: string;
  sender: "user" | "agent";
  agentName?: string;
  text: string;
  reasoning?: string[];
  citations?: { id: string; title: string; year: number }[];
  timestamp: string;
}

const initialMessages: Message[] = [
  {
    id: "1",
    sender: "agent",
    agentName: "Scholaris Synthesis Agent",
    text: "Welcome to your multi-agent research chat! I have indexed all 4 screened papers in your current literature corpus. What would you like to explore or synthesize today?",
    timestamp: "10:30 AM",
  },
  {
    id: "2",
    sender: "user",
    text: "What are the primary differences between iterative graph-guided retrieval and standard dense bi-encoder retrieval?",
    timestamp: "10:31 AM",
  },
  {
    id: "3",
    sender: "agent",
    agentName: "Scholaris Synthesis Agent",
    reasoning: [
      "1. Parsed query for comparative retrieval methodology.",
      "2. Retrieved section 3.2 from Rostova et al. [cs.AI:2403.08119].",
      "3. Cross-referenced with Sato et al. dense baseline [ACL 2023].",
      "4. Formulating structured comparison table with citations.",
    ],
    text: "Based on the screened corpus, there are three fundamental distinctions:\n\n1. **Dynamic Decision Horizon**: Standard dense bi-encoders perform single-pass top-k retrieval based on initial cosine similarity [Sato et al., 2023]. Iterative graph-guided retrieval maintains state across reasoning hops, deciding dynamically *if* and *what* auxiliary context is needed [Rostova et al., 2024].\n\n2. **Error Propagation**: Standard retrieval suffers from 'cascade failure' when early retrieved chunks are noisy. Graph-guided retrieval uses self-verification loops to prune contradictory nodes [Thorne et al., 2024].\n\n3. **Benchmark Performance**: On complex multi-hop QA, iterative retrieval demonstrated a **41% reduction in hallucination rates**, though at a cost of 1.8x higher inference latency.",
    citations: [
      { id: "1", title: "Benchmarking Adaptive Retrieval Strategies", year: 2024 },
      { id: "2", title: "Self-Correction & Verification Loops", year: 2024 },
      { id: "3", title: "Dense vs Hybrid Search", year: 2023 },
    ],
    timestamp: "10:31 AM",
  },
];

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [selectedAgent, setSelectedAgent] = useState("Synthesis Agent");
  const [isTyping, setIsTyping] = useState(false);
  const [expandedReasoning, setExpandedReasoning] = useState<Record<string, boolean>>({
    "3": true,
  });

  const chatBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSend = (textToSend?: string) => {
    const query = textToSend || input;
    if (!query.trim() || isTyping) return;

    const userMsg: Message = {
      id: String(Date.now()),
      sender: "user",
      text: query.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    setTimeout(() => {
      const agentMsg: Message = {
        id: String(Date.now() + 1),
        sender: "agent",
        agentName: `Scholaris ${selectedAgent}`,
        reasoning: [
          `1. Activated ${selectedAgent} reasoning chain in LangGraph.`,
          "2. Queried vector collection with semantic reranking.",
          "3. Synthesized evidence-grounded answer with inline citations.",
        ],
        text: `Analysis for "${query}":\n\nAcross the screened literature, the consensus indicates that incorporating human-in-the-loop validation checkpoints significantly stabilizes agent trajectory. Furthermore, combining BM25 lexical constraints with neural bi-encoders prevents drift in highly specialized scientific terminology.`,
        citations: [
          { id: "1", title: "Benchmarking Adaptive Retrieval", year: 2024 },
          { id: "4", title: "Automated Systematic Reviews", year: 2024 },
        ],
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, agentMsg]);
      setIsTyping(false);
    }, 1200);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const suggestedPrompts = [
    "What are the main research gaps identified in these papers?",
    "Summarize the evaluation metrics used across all studies.",
    "Draft a methodological comparison section for my literature review.",
  ];

  return (
    <div id="chat-page" className="w-full max-w-4xl mx-auto space-y-6 flex flex-col h-[calc(100vh-180px)] min-h-[550px]">
      {/* Header & Agent Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-black/5 pb-4 shrink-0">
        <div>
          <h1 className="font-serif text-3xl font-normal text-neutral-900 tracking-tight">
            Research Agent Chat
          </h1>
          <p className="text-xs sm:text-sm text-neutral-600 mt-0.5 font-sans-ui">
            Converse with specialized agents grounded in your screened papers.
          </p>
        </div>

        {/* Agent Persona Switcher */}
        <div className="flex items-center gap-1.5 bg-white/80 p-1 rounded-full border border-neutral-200/80 shadow-xs">
          {["Synthesis Agent", "Retrieval Agent", "Citation Agent"].map((agent) => (
            <button
              key={agent}
              onClick={() => setSelectedAgent(agent)}
              className={`px-3 py-1 rounded-full text-xs font-medium tracking-compact transition-all cursor-pointer ${
                selectedAgent === agent
                  ? "bg-neutral-900 text-white shadow-xs"
                  : "text-neutral-600 hover:text-black hover:bg-neutral-100"
              }`}
            >
              {agent}
            </button>
          ))}
        </div>
      </div>

      {/* Messages Thread Container */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1 sm:pr-2">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${
              msg.sender === "user" ? "items-end" : "items-start"
            }`}
          >
            {/* Sender Label */}
            <div className="text-[11px] text-neutral-500 mb-1 px-1 flex items-center gap-2">
              <span className="font-semibold text-neutral-700">
                {msg.sender === "user" ? "You" : msg.agentName}
              </span>
              <span>{msg.timestamp}</span>
            </div>

            {/* Bubble */}
            <div
              className={`max-w-[88%] sm:max-w-[80%] rounded-2xl p-4 sm:p-5 text-sm tracking-compact shadow-xs ${
                msg.sender === "user"
                  ? "bg-neutral-950 text-white rounded-tr-none"
                  : "bg-white text-neutral-900 border border-neutral-200/80 rounded-tl-none space-y-3"
              }`}
            >
              {/* Reasoning Accordion for Agent */}
              {msg.reasoning && (
                <div className="rounded-lg bg-neutral-50 border border-neutral-200/60 p-2.5 text-xs text-neutral-600">
                  <button
                    onClick={() =>
                      setExpandedReasoning((prev) => ({
                        ...prev,
                        [msg.id]: !prev[msg.id],
                      }))
                    }
                    className="flex items-center justify-between w-full text-left font-semibold text-neutral-800 cursor-pointer"
                  >
                    <span className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-emerald-500" />
                      Agent Reasoning Trajectory ({msg.reasoning.length} steps)
                    </span>
                    <span>{expandedReasoning[msg.id] ? "▲" : "▼"}</span>
                  </button>

                  {expandedReasoning[msg.id] && (
                    <div className="mt-2 space-y-1 font-mono text-[11px] text-neutral-600 border-t border-neutral-200/60 pt-2">
                      {msg.reasoning.map((step, i) => (
                        <div key={i}>{step}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Message text with newline support */}
              <div className="whitespace-pre-line leading-relaxed">
                {msg.text}
              </div>

              {/* Citations Grounding Chips */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="pt-2 border-t border-neutral-100 flex flex-wrap items-center gap-1.5">
                  <span className="text-[11px] font-semibold text-neutral-400">
                    Citations:
                  </span>
                  {msg.citations.map((c) => (
                    <Badge
                      key={c.id}
                      variant="accent"
                      className="text-[11px] py-0.5 px-2 bg-[#DFFFAA] text-black border border-black/10"
                    >
                      [{c.title} • {c.year}]
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex items-center gap-2 text-xs text-neutral-500 p-2">
            <span className="animate-spin text-base">🧠</span>
            <span>{selectedAgent} is synthesizing evidence across papers...</span>
          </div>
        )}

        <div ref={chatBottomRef} />
      </div>

      {/* Suggested Quick Prompts */}
      <div className="flex flex-wrap gap-2 shrink-0">
        {suggestedPrompts.map((p) => (
          <button
            key={p}
            onClick={() => handleSend(p)}
            className="text-xs px-3 py-1.5 rounded-full bg-white/80 hover:bg-white text-neutral-700 border border-neutral-200/80 shadow-2xs transition-colors cursor-pointer"
          >
            💡 {p}
          </button>
        ))}
      </div>

      {/* Chat Input Box */}
      <div className="bg-white rounded-2xl border border-neutral-200/90 shadow-md p-2 sm:p-2.5 flex items-center gap-2 shrink-0">
        <button
          type="button"
          title="Attach note or PDF"
          onClick={() => alert("Attach note or preprint to chat context")}
          className="p-2 text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors cursor-pointer"
        >
          📎
        </button>

        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Ask ${selectedAgent} anything about your literature...`}
          className="flex-1 bg-transparent border-0 outline-none text-sm text-neutral-900 placeholder:text-neutral-400 px-2 tracking-compact"
        />

        <button
          type="button"
          onClick={() => handleSend()}
          disabled={!input.trim() || isTyping}
          className={`w-9 h-9 rounded-full flex items-center justify-center text-white transition-all shadow-sm ${
            input.trim() && !isTyping
              ? "bg-[#4F6BF7] hover:bg-[#3D59E3] hover:scale-105 active:scale-95 cursor-pointer"
              : "bg-neutral-300 opacity-60 cursor-not-allowed"
          }`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18" />
          </svg>
        </button>
      </div>
    </div>
  );
}
