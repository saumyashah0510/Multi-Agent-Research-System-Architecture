import home1 from "../images/home_1.png";
import home2 from "../images/home_2.png";
import home3 from "../images/home_3.png";
import home4 from "../images/home_4.png";
import home5 from "../images/home_5.png";

export interface FeatureCardData {
  id: string;
  heading: string;
  subheading: string;
  description: string;
  image: string;
  imageAlt: string;
  imagePosition: "left" | "right";
  tint: "mint" | "lavender" | "sky";
}

export const featureCards: FeatureCardData[] = [
  {
    id: "how-it-works",
    heading: "How it works",
    subheading: "From a question to answers you can trust",
    description:
      "Tell Scholaris what you're researching. It finds the right papers, lets you pick what counts, and shows you how they connect ,  with every claim traceable back to its source.",
    image: home1,
    imageAlt: "Researcher exploring literature across arXiv, PubMed, and OpenAlex",
    imagePosition: "right",
    tint: "mint",
  },
  {
    id: "discover",
    heading: "Discover",
    subheading: "Ask in your own words",
    description:
      "Type your research question like you'd ask a colleague. Scholaris searches arXiv, PubMed, and OpenAlex at once, so you don't have to search each one yourself.",
    image: home2,
    imageAlt: "Automated search interface discovering academic literature across connected databases",
    imagePosition: "left",
    tint: "lavender",
  },
  {
    id: "review",
    heading: "Review",
    subheading: "You're always in control",
    description:
      "Scholaris shortlists papers that look relevant , you decide what actually belongs. One tap to approve, one tap to skip. Nothing gets used without your say-so.",
    image: home3,
    imageAlt: "Human-in-the-loop candidate paper screening and decision panel",
    imagePosition: "right",
    tint: "sky",
  },
  {
    id: "synthesis",
    heading: "Synthesis",
    subheading: "See the whole picture at once",
    description:
      "Scholaris reads your approved papers and shows you where they agree, where they clash, and what's still unanswered ,  so you're not piecing it together paper by paper.",
    image: home4,
    imageAlt: "Synthesis dashboard displaying comparison matrix, thematic clusters, and research gaps",
    imagePosition: "left",
    tint: "mint",
  },
  {
    id: "ask",
    heading: "Ask",
    subheading: "Talk to your papers directly",
    description:
      "Ask a question and get an answer pulled straight from your papers , with a citation attached, so you can check it yourself instead of taking Scholaris's word for it.",
    image: home5,
    imageAlt: "Conversational literature assistant with verifiable citation footnotes",
    imagePosition: "right",
    tint: "sky",
  },
];
