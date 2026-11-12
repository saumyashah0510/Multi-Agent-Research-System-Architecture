/**
 * ReviewDetail Page Component (/review/:reviewId)
 *
 * Assignee Task (Issues FE-06 / FE-07 / FE-08):
 * - Extract reviewId from route params (useParams)
 * - Fetch initial review status via GET /api/v1/reviews/{reviewId}
 * - Stream remaining stages 5 to 9 via WebSocket connection to /api/v1/ws/reviews/{reviewId}
 * - Display review topic header and session status
 * - Mount downstream pipeline progress tracker (Stages 5 to 9)
 * - Integrate accessible tab switcher (Report | Matrix | RAG Chat) when isCompleted is true
 * - Pass synthesized review to SynthesisReportViewer and methodology_matrix to MethodologyMatrix
 */

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import {
  FileText,
  Download,
  Check,
  Loader2,
  RefreshCw,
  AlertCircle,
  Network,
} from "lucide-react";
import { cn } from "../lib/utils";
import DownstreamProgress from "../components/pipeline/DownstreamProgress";
import RetryBanner from "../components/pipeline/RetryBanner";
import SynthesisReportViewer, {
  formatReportAsMarkdown,
} from "../components/dashboard/SynthesisReportViewer";
import ReviewChat from "../components/chat/ReviewChat";
import CitationKnowledgeGraph from "../components/graph/CitationKnowledgeGraph";
import { getReviewStatus, getReviewPdfDownloadUrl, retryReviewPipeline } from "../lib/api";
import { SynthesizedReview } from "../types";

const SAMPLE_FALLBACK_REPORT: SynthesizedReview = {
  title:
    "Architectures and Governance in Autonomous Multi-Agent Systems: A Systematic Synthesis of Emergent Paradigms",
  executive_summary: [
    "The field of Multi-Agent Systems (MAS) has recently undergone a paradigm shift, transitioning from traditional symbolic logic-based architectures toward dynamic, agentic workflows powered by Large Language Models (LLMs). This evolution addresses the fundamental challenges of coordinating complex decision-making processes in heterogeneous environments. By leveraging specialized agents for task decomposition, hypothesis generation, and experimental validation, contemporary frameworks now aim to automate scientific discovery, medical diagnosis, and enterprise-level logistics, marking a significant departure from rigid, manually programmed systems toward emergent, goal-oriented autonomy.",
    "The reviewed corpus highlights a convergence toward hybrid architectures. These systems typically integrate retrieval-augmented generation (RAG) for evidentiary support, knowledge graphs (KG) for structural domain grounding, and multi-agent collaboration protocols to optimize computational resource utilization. Approaches range from hierarchical supervisors, such as Project Synapse [Yadav et al., 2026], to specialized scientific discovery agents like Robin [Ghareeb et al., 2026]. These models often employ meta-gating mechanisms and progress-guided routing to manage the significant operating costs and context accumulation associated with multi-step agentic execution, as demonstrated by the ProgRouter framework [Li et al., 2026].",
    "Empirical benchmarks and methodological evaluations indicate that multi-agent systems significantly outperform single-agent baselines in goal success rates and reasoning quality across diverse domains, including software development, mathematical reasoning, and clinical decision support [Li et al., 2026; Shu et al., 2024]. Innovations such as PROV-AGENT [Souza et al., 2025] and the EGA V9 governance framework [Byun, 2026] have established new standards for provenance tracking and execution monitoring, ensuring that agents can operate with transparency and reliability. However, the field faces critical trade-offs between architectural complexity, runtime performance, and the necessity for human-in-the-loop oversight to mitigate risks such as hallucination and execution divergence.",
    "Despite these advancements, persistent challenges remain regarding the security, verifiability, and scalability of these systems. Current research gaps emphasize the need for formally verifiable architectures capable of separating instruction channels from data channels, as well as the creation of standardized benchmarks for agent safety in enterprise applications. As the field moves toward more autonomous self-improving agents, the tension between recursive development capability and model alignment highlights the requirement for more robust, auditable infrastructure to ensure that agentic decisions remain consistent with domain-specific requirements and safety governance.",
  ].join("\n\n"),
  thematic_clusters: [
    {
      theme: "Agentic Frameworks and Collaborative Architectures",
      summary:
        "This cluster explores the architectural design choices in multi-agent systems. Research underscores a move toward hierarchical decomposition and dynamic coordination. Frameworks like Project Synapse [Yadav et al., 2026] demonstrate that hierarchical structures outperform flat models by delegating strategic versus tactical tasks. Similarly, MedAide [Yang et al., 2024] and Robin [Ghareeb et al., 2026] highlight the efficacy of intent-aware role rotation and specialized literature-search agents, respectively. These systems collectively suggest that effective agent collaboration requires not just task distribution, but also mechanisms for managing information fusion, cross-agent consistency, and context-dependent routing as defined in the ProgRouter framework [Li et al., 2026].",
      citations: [
        "A Survey of Multi-Agent Deep Reinforcement Learning with Communication",
        "A Methodology to Engineer and Validate Dynamic Multi-level Multi-agent Based Simulations",
        "Robin: A multi-agent system for scientific discovery",
        "Project Synapse: A Hierarchical Multi-Agent Framework",
        "ProgRouter: Online Progress-Guided Orchestration",
        "MedAide: Information Fusion and Anatomy of Medical Intents via LLM-based Agent Collaboration",
      ],
    },
    {
      theme: "Governance, Provenance, and Trustworthy Execution",
      summary:
        "With the rise of agentic autonomy, ensuring accountability has become a primary research focus. The PROV-AGENT model [Souza et al., 2025] extends existing standards to capture agentic metadata, facilitating root-cause analysis and traceability. Furthermore, the EGA V9 framework [Byun, 2026] introduces deterministic runtime governance, demonstrating 100% detection performance in workflow-divergence scenarios. This theme emphasizes that for agents to be adopted in critical fields—such as medicine or IT support—they must offer more than just performance; they must provide auditable, provenance-aware execution paths that distinguish between trial evidence, real-world data, and LLM-generated claims, as seen in the MES system [Li et al., 2026].",
      citations: [
        "PROV-AGENT: Unified Provenance for Tracking AI Agent Interactions in Agentic Workflows",
        "MES: A Multi-Agent Evidence Synthesis System",
        "Who Governs Autonomous AI Execution? Execution Governance AI (EGA) V9",
        "Autonomous Research Project Management as an Agent Skill",
        "AI-Driven Autonomous Knowledge Assistants for Enterprise IT Helpdesks",
      ],
    },
    {
      theme: "Autonomous Discovery and Empirical Validation",
      summary:
        "This theme examines systems designed to close the loop on scientific and technical discovery. Autonomous agents are moving from simple Q&A interfaces toward active experimentation, such as the Robin system's identification of therapeutic candidates for retinal degradation [Ghareeb et al., 2026]. Research by Chen et al. [2026] on autonomous research project management further validates the potential of agents to handle long-horizon research tasks with minimal human steering. These studies underscore the necessity of rigorous, falsifiable review gates and the transition toward agent-accessible data formats as critical components for accelerating scientific advancement while maintaining reproducibility.",
      citations: [
        "A multi-agent system for automating scientific discovery (Robin)",
        "Autonomous Research Project Management as an Agent Skill",
        "Autonomous AI research agents in pancreatic ductal adenocarcinoma immunology",
        "Closed-loop artificial intelligence agents for animal epidemic prediction and decision support",
      ],
    },
    {
      theme: "Classification, Taxonomies, and Future Benchmarks",
      summary:
        "The maturity of the multi-agent field requires common classification frameworks. The ASTELD framework [Li et al., 2026] serves as a foundational taxonomy, evaluating agents across six axes including security and deployment topology. This work bridges the gap between fragmented platform implementations, identifying 'empty regions' in the current ecosystem, such as the lack of local-first deployment options with enterprise-grade security. Concurrently, the Meta-Agent Challenge [Lu et al., 2026] pushes the field to test the recursive capabilities of agents to develop other agents, providing a critical empirical proxy for future autonomous AI research.",
      citations: [
        "ASTELD: A Six-Axis Classification Framework for Autonomous AI Agents",
        "The Meta-Agent Challenge: Are Current Agents Capable of Autonomous Agent Development?",
        "Large Language Models Penetration in Scholarly Writing and Peer Review",
      ],
    },
  ],
  methodology_matrix: [
    {
      method_name: "Multi-Agent Reinforcement Learning (MARL)",
      papers_used: ["A Survey of Multi-Agent Deep Reinforcement Learning with Communication"],
      strengths: [
        "Enhanced coordination through communication protocols",
        "Improved collaborative learning performance",
      ],
      limitations: ["Lacks systematic structural classification"],
    },
    {
      method_name: "Agent-Based Modeling (ABM)",
      papers_used: [
        "A Methodology to Engineer and Validate Dynamic Multi-level Multi-agent Based Simulations",
        "From Model-Based Screening to Data-Driven Surrogates",
      ],
      strengths: [
        "Scalable across domains",
        "Systematic parameter exploration",
        "Automatic identification of unstable regions",
      ],
      limitations: [
        "Curse of dimensionality",
        "Stochasticity handling",
        "Computational resource intensive",
      ],
    },
    {
      method_name: "Agentic RAG & Knowledge Graph Integration",
      papers_used: [
        "HySemRAG: A Hybrid Semantic Retrieval-Augmented Generation Framework",
        "MES: A Multi-Agent Evidence Synthesis System",
        "Integrating knowledge graphs with ancient Chinese medicine classics",
      ],
      strengths: [
        "High semantic similarity",
        "Traceable provenance",
        "Effective integration of heterogeneous data",
      ],
      limitations: [
        "Reliability on open-access availability",
        "Underdeveloped automated KG extraction",
      ],
    },
    {
      method_name: "Autonomous Scientific Discovery Systems",
      papers_used: [
        "A multi-agent system for automating scientific discovery (Robin)",
        "Autonomous Research Project Management as an Agent Skill",
      ],
      strengths: [
        "Fully automated hypothesis-experiment-analysis cycles",
        "Demonstrated therapeutic candidate discovery",
      ],
      limitations: [
        "Determinism concerns",
        "Heavy dependence on specific LLM models",
        "Rigid tool-calling sequences",
      ],
    },
    {
      method_name: "Provenance-Aware Governance & Monitoring",
      papers_used: [
        "PROV-AGENT",
        "Who Governs Autonomous AI Execution? Execution Governance AI (EGA) V9",
      ],
      strengths: [
        "Real-time execution observability",
        "Deterministic replay and failure detection",
        "Provenance tracking",
      ],
      limitations: ["Post-incident restriction challenges"],
    },
    {
      method_name: "Taxonomy-Based Classification (ASTELD)",
      papers_used: ["ASTELD: A Six-Axis Classification Framework for Autonomous AI Agents"],
      strengths: [
        "Discriminative utility for platform comparisons",
        "Identifies ecosystem design voids",
      ],
      limitations: [
        "Limited sample sizes for framework evaluation",
        "Reflects dominant configurations, not exhaustive capabilities",
      ],
    },
  ],
  research_gaps: [
    "How can a formally verifiable architecture enforce structural separation between LLM instruction channels and untrusted data channels to fundamentally eliminate prompt injection as an authorization bypass?",
    "Can a universal, capability-based permission model for autonomous agents provide fine-grained resource control without degrading performance or hindering the composability required for open agent marketplaces?",
    "What formal specifications and evaluation metrics define 'approval correctness' for human-in-the-loop workflows where the representation of an action differs between user-approval time and machine-execution time?",
    "How can agentic supply chain risks be mitigated when malicious logic is encoded as semantically meaningful natural language instructions, rendering static code-analysis techniques ineffective?",
    "In the context of autonomous agent research, how can standardized benchmarks be established to quantify agent reliability and safety for enterprise adoption while accounting for the high-variance nature of LLM reasoning?",
  ],
  conclusion: [
    "The literature reviewed illustrates a transformative trajectory for multi-agent systems, shifting from academic abstraction to practical, high-stakes application in clinical, scientific, and enterprise contexts. The integration of provenance-aware governance, hybrid memory systems, and rigorous meta-agent evaluation frameworks demonstrates a significant maturing of the field. However, to ensure safe and widespread deployment, future research must move beyond mere performance metrics to prioritize interpretability and robustness against adversarial instruction-based manipulation.",
    "Moving forward, the field requires a paradigm of 'design for trust,' where structural safety—such as deterministic replay and strict permissioning—is incorporated into the architecture from inception. Developing universal taxonomies and standardized benchmarks, as initiated by ASTELD and the Meta-Agent Challenge, is essential for unifying the currently fragmented landscape. The ultimate objective is to cultivate autonomous agents that act not as 'black-box' solvers, but as transparent, verifiable participants in the scholarly and industrial discovery process, capable of navigating the complex interplay between human intent and automated execution.",
  ].join("\n\n"),
  references: [
    {
      title: "A Survey of Multi-Agent Deep Reinforcement Learning with Communication",
      authors: ["Changxi Zhu", "Mehdi Dastani", "Shihan Wang"],
      year: 2022,
      url: "https://arxiv.org/pdf/2203.08975v2",
      matched_passage:
        "Communication is an effective mechanism for coordinating the behaviors of multiple agents",
    },
    {
      title:
        "A Methodology to Engineer and Validate Dynamic Multi-level Multi-agent Based Simulations",
      authors: ["Jean-Baptiste Soyez", "Gildas Morvan", "Daniel Dupont", "Rochdi Merzouki"],
      year: 2013,
      url: "https://arxiv.org/pdf/1311.5108v1",
      matched_passage:
        "This methodology permits the engineering of dynamic multi-level agent-based models, to represent complex systems over several scales and domains of interest.",
    },
    {
      title:
        "From Model-Based Screening to Data-Driven Surrogates: A Multi-Stage Workflow for Exploring Stochastic Agent-Based Models",
      authors: ["Paul Saves", "Matthieu Mastio", "Nicolas Verstaevel", "Benoit Gaudou"],
      year: 2026,
      url: "https://arxiv.org/pdf/2604.03350v1",
      matched_passage:
        "We present a multi-stage pipeline integrating the systematic design of experiments with machine learning surrogates.",
    },
    {
      title:
        "HySemRAG: A Hybrid Semantic Retrieval-Augmented Generation Framework for Automated Literature Synthesis and Methodological Gap Analysis",
      authors: ["Alejandro Godinez"],
      year: 2025,
      url: "https://arxiv.org/pdf/2508.05666v1",
      matched_passage:
        "Evaluation across 643 observations from 60 testing sessions demonstrates structured field extraction achieving 35.1% higher semantic similarity scores",
    },
    {
      title: "MES: A Multi-Agent Evidence Synthesis System for Medical Decision-Making",
      authors: [
        "Haoyang Li",
        "Weishen Pan",
        "Suraj Rajendran",
        "Chengxi Zang",
        "Judy Gabeskiria",
        "Valencia Liu",
        "Vivian Feng",
        "Mahitha Penmetsa",
        "Lydia Lin",
        "Atindra Bhalchandra Jayakar",
        "Ayham Boucher",
        "Edward J Schenck",
        "He S Yang",
        "Fei Wang",
      ],
      year: 2026,
      url: "https://www.medrxiv.org/content/medrxiv/early/2026/09/21/2026.09.15.26362921.full.pdf",
      matched_passage:
        "MES also provides claim-level provenance tracking and cross-agent consistency checking",
    },
    {
      title: "A multi-agent system for automating scientific discovery",
      authors: [
        "Ali E Ghareeb",
        "Benjamin Chang",
        "Ludovico Mitchener",
        "Angela Yiu",
        "Caralyn J Szostkiewicz",
        "Dmytro Shved",
        "Gavin J Gyimesi",
        "Jon M Laurent",
        "Samantha M Wright",
        "Muhammed T Razzak",
        "Andrew D White",
        "Silvia C Finnemann",
        "Michaela M Hinks",
        "Samuel G Rodriques",
      ],
      year: 2026,
      url: "https://arxiv.org/pdf/2505.13400",
    },
    {
      title:
        "Integrating knowledge graphs with ancient Chinese medicine classics: challenges and future prospects of multi-agent system convergence",
      authors: ["Shate Xiang", "Huanxiang Lin", "Fen Cai", "Zhehan Jiang"],
      year: 2025,
      url: "https://cmjournal.biomedcentral.com/counter/pdf/10.1186/s13020-025-01226-7",
      matched_passage:
        "automated extraction and intelligent integration within KG remain underdeveloped.",
    },
    {
      title: "Logic-based technologies for multi-agent systems: a systematic literature review",
      authors: ["Roberta Calegari", "Giovanni Ciatto", "Viviana Mascardi", "Andrea Omicini"],
      year: 2021,
      url: "https://link.springer.com/content/pdf/10.1007/s10458-020-09478-3.pdf",
    },
    {
      title: "Large Language Models Penetration in Scholarly Writing and Peer Review",
      authors: ["Li Zhou", "Ruijie Zhang", "Xunlian Dai", "Daniel Hershcovich", "Haizhou Li"],
      year: 2025,
      url: "https://arxiv.org/pdf/2502.11193v1",
    },
    {
      title:
        "PROV-AGENT: Unified Provenance for Tracking AI Agent Interactions in Agentic Workflows",
      authors: [
        "Renan Souza",
        "Amal Gueroudji",
        "Stephen DeWitt",
        "Daniel Rosendo",
        "Tirthankar Ghosal",
        "Robert Ross",
        "Prasanna Balaprakash",
        "Rafael Ferreira da Silva",
      ],
      year: 2025,
      url: "https://arxiv.org/pdf/2508.02866v3",
      matched_passage:
        "Data stream in near real time from the experimental facility to HPC systems",
    },
    {
      title:
        "ASTELD: A Six-Axis Classification Framework for Autonomous AI Agents - Design, Evaluation, and an OpenClaw Case Study",
      authors: [
        "Siyuan Li",
        "Peng Shu",
        "Churan Yu",
        "Peilong Wang",
        "Ruidong Zhang",
        "Bowen Guo",
        "Xinliang Li",
        "Ruiyu Yan",
        "Arif Hassan Zidan",
        "Yi Pan",
        "Wei Ruan",
        "Lifeng Chen",
        "Junhao Chen",
        "Zhaojun Ding",
        "Yiwei Li",
        "Zhengliang Liu",
        "Haixing Dai",
        "Lin Zhao",
        "Yu Bao",
        "Xiang Li",
        "Wei Zhang",
        "Tianming Liu",
      ],
      year: 2026,
      url: "https://arxiv.org/pdf/2608.05201v1",
      matched_passage:
        "We evaluate its discriminative and explanatory utility by mapping eight representative frameworks",
    },
    {
      title: "AI Literature Review Suite",
      authors: ["David A. Tovar"],
      year: 2023,
      url: "https://arxiv.org/pdf/2308.02443v1",
    },
    {
      title:
        "The Meta-Agent Challenge: Are Current Agents Capable of Autonomous Agent Development?",
      authors: [
        "Xinyu Lu",
        "Tianshu Wang",
        "Pengbo Wang",
        "zujie wen",
        "Zhiqiang Zhang",
        "Jun Zhou",
        "Boxi Cao",
        "Yaojie Lu",
        "Hongyu Lin",
        "Xianpei Han",
        "Le Sun",
      ],
      year: 2026,
      url: "https://arxiv.org/pdf/2606.04455v1",
    },
    {
      title:
        "ProgRouter: Online Progress-Guided Orchestration for Multi-Agent LLM Workflows under Quality-Cost Tradeoffs",
      authors: ["Songyuan Li", "Ahmed M. Abdelmoniem", "Shiqiang Wang"],
      year: 2026,
      url: "https://arxiv.org/pdf/2608.25992v2",
    },
    {
      title:
        "Project Synapse: A Hierarchical Multi-Agent Framework with Hybrid Memory for Autonomous Resolution of Last-Mile Delivery Disruptions",
      authors: ["Arin Gopalan Yadav", "Varad Dherange", "Kumar Shivam"],
      year: 2026,
      url: "https://arxiv.org/pdf/2601.08156v1",
    },
    {
      title:
        "Autonomous AI research agents in pancreatic ductal adenocarcinoma immunology: from multimodal evidence to experimental validation",
      authors: ["Yang Li", "Yu Li", "Rong Huang", "Zhi-Qiang San", "Jun-Feng Ye"],
      year: 2026,
      url: "https://www.frontiersin.org/journals/immunology/articles/10.3389/fimmu.2026.1983838/pdf",
    },
    {
      title:
        "Closed-loop artificial intelligence agents for animal epidemic prediction and decision support in livestock farming: a review",
      authors: ["Yuzhi Wang", "Yingtong Zhou", "Liyu Li", "Huiling Xu", "Wangze Ni", "Xiaoliang Li"],
      year: 2026,
      url: "https://www.frontiersin.org/journals/veterinary-science/articles/10.3389/fvets.2026.1968632/pdf",
    },
    {
      title:
        "Who Governs Autonomous AI Execution? Execution Governance AI (EGA) V9: A Deterministic Runtime Governance Framework for Trustworthy Autonomous Workflows",
      authors: ["DaeJung Byun"],
      year: 2026,
      url: "https://www.researchsquare.com/article/rs-10863696/latest.pdf",
      matched_passage:
        "EGA V9 addresses this challenge through a deterministic runtime-governance framework that combines deterministic replay... and fail-closed containment",
    },
    {
      title:
        "Towards Effective GenAI Multi-Agent Collaboration: Design and Evaluation for Enterprise Applications",
      authors: ["Raphael Shu", "Nilaksh Das", "Michelle Yuan", "Monica Sunkara", "Yi Zhang"],
      year: 2024,
      url: "https://arxiv.org/pdf/2412.05449v1",
    },
    {
      title: "Envisioning Sensemaking in Multi-Human, Multi-Agent Collaborative Knowledge Work",
      authors: ["Zhitong Guan", "Soo Young Rieh"],
      year: 2026,
      url: "https://arxiv.org/pdf/2606.09840v1",
    },
    {
      title:
        "MedAide: Information Fusion and Anatomy of Medical Intents via LLM-based Agent Collaboration",
      authors: [
        "Dingkang Yang",
        "Jinjie Wei",
        "Mingcheng Li",
        "Jiyao Liu",
        "Lihao Liu",
        "Ming Hu",
        "Junjun He",
        "Yakun Ju",
        "Wei Zhou",
        "Yang Liu",
        "Lihua Zhang",
      ],
      year: 2024,
      url: "https://arxiv.org/pdf/2410.12532v3",
      matched_passage:
        "propose MedAide, an LLM-based medical multi-agent collaboration framework designed to enable intent-aware information fusion and coordinated reasoning across specialized healthcare domains.",
    },
    {
      title:
        "Autonomous Research Project Management as an Agent Skill: A Case Study in Exact Spectral Spatial Regression",
      authors: ["Alexander Chen", "Jeffrey Meng", "Bram Hoex", "Tong Xie"],
      year: 2026,
      url: "https://arxiv.org/pdf/2609.31683v1",
    },
    {
      title: "AI-Driven Autonomous Knowledge Assistants for Enterprise IT Helpdesks",
      authors: ["Anumandla Mukesh"],
      year: 2023,
      url: "https://www.ijrai.org/index.php/ijrai/article/download/449/417",
    },
  ],
};

const ReviewDetailInner: React.FC = () => {
  const { reviewId } = useParams<{ reviewId: string }>();
  const [searchParams] = useSearchParams();
  const isMockParam = searchParams.get("mock") === "true";
  const tabParam = (searchParams.get("tab") || "").toLowerCase();

  const [isCompleted, setIsCompleted] = useState(false);
  const [isFailed, setIsFailed] = useState(false);
  const [failedMessage, setFailedMessage] = useState<string | null>(null);
  const isChatView = tabParam === "chat";
  const isGraphView = tabParam === "graph";
  const [copiedMarkdown, setCopiedMarkdown] = useState(false);
  const [reviewTopic, setReviewTopic] = useState<string | null>(null);
  const [synthesizedReport, setSynthesizedReport] = useState<SynthesizedReview | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Load review status and synthesized report via GET /api/v1/reviews/{reviewId}
  const loadReviewData = useCallback(async () => {
    if (!reviewId) return null;
    try {
      const data = await getReviewStatus(reviewId);
      if (data?.query || data?.user_query) {
        setReviewTopic(data.query || data.user_query);
      }
      const normStatus = String(data?.status || "").toLowerCase();
      if (normStatus === "completed" || normStatus === "synthesis_completed") {
        setIsCompleted(true);
        setIsFailed(false);
        if (data?.synthesized_review) {
          setSynthesizedReport(data.synthesized_review);
          setFetchError(null);
        }
      } else if (normStatus === "failed") {
        setIsFailed(true);
        setFailedMessage(
          data?.error_message ||
            "Pipeline was interrupted. Click 'Retry from Failed Step' to resume from your latest checkpoint."
        );
      } else {
        setIsFailed(false);
      }
      return data;
    } catch (err) {
      console.warn("Could not retrieve review status:", err);
      return null;
    }
  }, [reviewId]);

  useEffect(() => {
    if (!reviewId) return;

    // Reset review state on reviewId change to avoid displaying stale data
    setReviewTopic(null);
    setSynthesizedReport(null);
    setIsCompleted(false);
    setRetryCount(0);
    setFetchError(null);

    let isMounted = true;
    loadReviewData().then((data) => {
      if (!isMounted || !data) return;
    });

    return () => {
      isMounted = false;
    };
  }, [reviewId, loadReviewData]);

  const handlePipelineComplete = useCallback(() => {
    setIsCompleted(true);
    setRetryCount(0);
    setFetchError(null);
    loadReviewData();
  }, [loadReviewData]);

  // Auto-retry polling if pipeline completed but synthesized_review is not yet available
  useEffect(() => {
    if (!isCompleted || synthesizedReport || retryCount >= 5) return;

    const timer = setTimeout(async () => {
      setRetryCount((prev) => prev + 1);
      const res = await loadReviewData();
      if (!res?.synthesized_review && retryCount + 1 >= 5) {
        setFetchError("Synthesis report is taking longer than expected to persist.");
      }
    }, 3000);

    return () => clearTimeout(timer);
  }, [isCompleted, synthesizedReport, retryCount, loadReviewData]);

  const handleManualRetry = async () => {
    setIsRetrying(true);
    setFetchError(null);
    try {
      const res = await loadReviewData();
      if (!res?.synthesized_review) {
        setFetchError("Report not available yet. Please try again in a few moments.");
      }
    } finally {
      setIsRetrying(false);
    }
  };

  // Show fabricated sample data only in explicit mock/dev mode, never as real results
  const activeReport: SynthesizedReview | null =
    synthesizedReport ||
    (isMockParam || import.meta.env.DEV
      ? {
          ...SAMPLE_FALLBACK_REPORT,
          title: reviewTopic
            ? `Comparative Literature Synthesis: ${reviewTopic}`
            : SAMPLE_FALLBACK_REPORT.title,
        }
      : null);

  const handleExportMarkdown = () => {
    if (!activeReport) return;
    const markdown = formatReportAsMarkdown(activeReport);
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const slug = (activeReport.title || reviewId || "literature-review")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 60);
    link.href = url;
    link.download = `${slug || "literature-review"}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(markdown).catch(() => {});
    }
    setCopiedMarkdown(true);
    window.setTimeout(() => setCopiedMarkdown(false), 2000);
  };

  return (
    <div className="w-full max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Session Header Bar */}
      <div className="border-b border-neutral-200/80 pb-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="min-w-0">
          {isChatView && (
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--color-sky-dark)] mb-1.5">
              Review Q&A
            </p>
          )}
          <h1 className="text-2xl sm:text-3xl font-serif font-bold text-neutral-900 leading-tight">
            {activeReport?.title || reviewTopic || "Literature Review Session"}
          </h1>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {isCompleted && !isChatView && (
            <>
              <a
                href={getReviewPdfDownloadUrl(reviewId || "")}
                target="_blank"
                rel="noopener noreferrer"
                style={{ borderRadius: "var(--radius-sm)" }}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-neutral-900 text-white text-xs font-semibold hover:bg-neutral-800 transition-colors shadow-xs"
                title="Download PDF Synthesis Report"
              >
                <Download className="w-3.5 h-3.5" />
                <span>PDF</span>
              </a>

              {activeReport && (
              <button
                type="button"
                onClick={handleExportMarkdown}
                style={{ borderRadius: "var(--radius-sm)" }}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white border border-neutral-200 text-neutral-800 text-xs font-semibold hover:bg-neutral-50 transition-colors cursor-pointer shadow-xs"
                title="Download Markdown report and copy to clipboard"
              >
                {copiedMarkdown ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-[var(--color-success)]" />
                    <span>Exported</span>
                  </>
                ) : (
                  <>
                    <FileText className="w-3.5 h-3.5" />
                    <span>Markdown</span>
                  </>
                )}
              </button>
            )}
          </>
        )}
        </div>
      </div>

      {/* Mid-Pipeline Retry Banner (Issue FE-13) */}
      {isFailed && (
        <RetryBanner
          reviewId={reviewId || ""}
          errorMessage={failedMessage || undefined}
          onRetry={async () => {
            if (!reviewId) return;
            await retryReviewPipeline(reviewId);
            setIsFailed(false);
            loadReviewData();
          }}
          className="mb-6"
        />
      )}

      {/* Downstream Checkpoints Tracker (Stages 5 to 9) */}
      <DownstreamProgress
        reviewId={reviewId}
        isCompleted={isCompleted}
        onComplete={handlePipelineComplete}
        isMock={isMockParam}
      />

      {/* Synthesis Report, Interactive RAG Chat, or Citation Graph View */}
      {isCompleted && (
        <div className="space-y-5 animate-in fade-in duration-300">
          {/* Tab Switcher */}
          <div className="flex items-center gap-2 border-b border-neutral-200/80 pb-3">
            <Link
              to={`/review/${reviewId}`}
              className={cn(
                "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors",
                !isChatView && !isGraphView
                  ? "bg-neutral-900 text-white shadow-2xs"
                  : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
              )}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Synthesis Report</span>
            </Link>
            <Link
              to={`/review/${reviewId}?tab=graph`}
              className={cn(
                "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors",
                isGraphView
                  ? "bg-neutral-900 text-white shadow-2xs"
                  : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
              )}
            >
              <Network className="w-3.5 h-3.5" />
              <span>Knowledge Graph</span>
            </Link>
            <Link
              to={`/review/${reviewId}?tab=chat`}
              className={cn(
                "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors",
                isChatView
                  ? "bg-neutral-900 text-white shadow-2xs"
                  : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
              )}
            >
              <span>Q&A Chat</span>
            </Link>
          </div>

          {isChatView ? (
            reviewId ? (
              <ReviewChat reviewId={reviewId} />
            ) : (
              <div className="w-full bg-white rounded-2xl border border-neutral-200/90 shadow-xs p-8 text-center text-neutral-500 text-xs sm:text-sm">
                No literature review ID provided in the route.
              </div>
            )
          ) : isGraphView ? (
            <CitationKnowledgeGraph reviewId={reviewId || ""} />
          ) : activeReport ? (
            <SynthesisReportViewer report={activeReport} />
          ) : (
            <div className="w-full bg-white rounded-2xl border border-neutral-200/90 shadow-xs p-8 text-center space-y-4">
              <div className="w-10 h-10 mx-auto rounded-full bg-indigo-50 flex items-center justify-center text-indigo-600">
                {fetchError && retryCount >= 5 ? (
                  <AlertCircle className="w-5 h-5 text-amber-600" />
                ) : (
                  <Loader2 className="w-5 h-5 animate-spin" />
                )}
              </div>
              <div>
                <h3 className="font-serif text-lg font-bold text-neutral-900">
                  {fetchError && retryCount >= 5
                    ? "Report Generation in Progress"
                    : "Finalizing Literature Synthesis..."}
                </h3>
                <p className="text-xs text-neutral-500 max-w-md mx-auto mt-1">
                  {fetchError ||
                    "Downstream agents completed analysis. The structured synthesis report and comparative matrix are currently being assembled."}
                </p>
              </div>
              <div>
                <button
                  type="button"
                  onClick={handleManualRetry}
                  disabled={isRetrying}
                  style={{ borderRadius: "var(--radius-sm)" }}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50"
                >
                  <RefreshCw className={cn("w-3.5 h-3.5", isRetrying && "animate-spin")} />
                  <span>{isRetrying ? "Checking..." : "Refresh Report"}</span>
                </button>
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  );
};

export const ReviewDetail: React.FC = () => {
  const { reviewId } = useParams<{ reviewId: string }>();
  return <ReviewDetailInner key={reviewId} />;
};

export default ReviewDetail;
