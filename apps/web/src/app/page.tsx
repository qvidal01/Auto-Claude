"use client";

import { CloudAuthenticated, CloudUnauthenticated, CloudAuthLoading } from "@/providers/AuthGate";
import { useCloudMode } from "@/hooks/useCloudMode";
import { getConvexReact, getConvexApi } from "@/lib/convex-imports";
import { AppShell } from "@/components/layout";
import Link from "next/link";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";

function CloudDashboard() {
  const { useQuery, useMutation } = getConvexReact();
  const { api } = getConvexApi();
  const { t } = useTranslation(["pages", "common"]);

  const user = useQuery(api.users.me);
  const ensureUser = useMutation(api.users.ensureUser);

  useEffect(() => {
    if (user === null) {
      ensureUser();
    }
  }, [user, ensureUser]);

  if (!user) return <div className="flex h-screen items-center justify-center">{t("common:loading")}</div>;

  return <AppShell />;
}

function SelfHostedDashboard() {
  return <AppShell />;
}

function LandingPage() {
  const { t } = useTranslation(["pages", "common"]);

  return (
    <div className="flex h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-4xl font-bold">{t("pages:home.landing.title")}</h1>
      <p className="text-gray-600">{t("pages:home.landing.subtitle")}</p>
      <Link
        href="/login"
        className="rounded-lg bg-blue-600 px-6 py-3 text-white hover:bg-blue-700"
      >
        {t("common:buttons.getStarted")}
      </Link>
    </div>
  );
}

export default function HomePage() {
  const { isCloud } = useCloudMode();
  const { t } = useTranslation("common");

  if (!isCloud) {
    return (
      <main>
        <SelfHostedDashboard />
      </main>
    );
  }

  return (
    <main>
      <CloudAuthLoading>
        <div className="flex h-screen items-center justify-center">{t("loading")}</div>
      </CloudAuthLoading>
      <CloudUnauthenticated>
        <LandingPage />
      </CloudUnauthenticated>
      <CloudAuthenticated>
        <CloudDashboard />
      </CloudAuthenticated>
    </main>
  );
}
