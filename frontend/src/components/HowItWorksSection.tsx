import FeatureCard from "./FeatureCard";
import { featureCards } from "../data/featureCards";

export default function HowItWorksSection() {
  return (
    <div className="w-full flex flex-col gap-8 md:gap-12">
      {featureCards.map((card) => (
        <FeatureCard
          key={card.id}
          id={card.id}
          heading={card.heading}
          subheading={card.subheading}
          description={card.description}
          image={card.image}
          imageAlt={card.imageAlt}
          imagePosition={card.imagePosition}
          tint={card.tint}
        />
      ))}
    </div>
  );
}
