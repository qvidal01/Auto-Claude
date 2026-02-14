import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Auto Claude - Dashboard",
  description: "AI-powered software development platform",
};

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
