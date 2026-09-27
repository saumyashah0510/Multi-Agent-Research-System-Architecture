export interface FeatureCardData {
  id: string;
  heading: string;
  subheading: string;
  description: string;
  image: string;
  imageAlt?: string;
  imagePosition: "left" | "right";
  tint: "mint" | "lavender" | "sky";
}

export const featureCards: FeatureCardData[] = [
  {
    id: "multi-agent-search",
    heading: "01 / Multi-Agent Discovery",
    subheading: "Automated Academic Search across ArXiv & OpenAlex",
    description:
      "Autonomous search agents execute expanded academic queries, retrieve paper metadata, and perform semantic deduplication in seconds.",
    image: "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?q=80&w=600&auto=format&fit=crop",
    imageAlt: "Academic paper discovery",
    imagePosition: "right",
    tint: "mint",
  },
  {
    id: "human-in-the-loop",
    heading: "02 / Human-in-the-Loop",
    subheading: "Interactive Screening & Approval Control",
    description:
      "Review candidate papers with relevance scoring. Approve or reject papers before vector embedding and report synthesis.",
    image: "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?q=80&w=600&auto=format&fit=crop",
    imageAlt: "Human in the loop approval",
    imagePosition: "left",
    tint: "lavender",
  },
  {
    id: "structured-synthesis",
    heading: "03 / Automated Synthesis",
    subheading: "Structured Methodology Matrices & Citation Reports",
    description:
      "Generates comprehensive literature reviews complete with methodology comparison matrices, identified research gaps, and formatted APA/IEEE references.",
    image: "https://images.unsplash.com/photo-1507842217343-583bb7270b66?q=80&w=600&auto=format&fit=crop",
    imageAlt: "Literature review synthesis",
    imagePosition: "right",
    tint: "sky",
  },
];
