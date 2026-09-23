// Next.js Root Layout Starter Skeleton
// TODO (Assignee - Frontend Developer): Configure application layout and theme styling.

export const metadata = {
  title: "Multi-Agent Academic Literature Review Assistant",
  description: "Autonomous multi-agent research pipeline for literature synthesis.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}
