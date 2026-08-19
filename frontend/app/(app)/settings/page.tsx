"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { useToast } from "@/components/ui/Toast";
import { getActiveModelDetail } from "@/lib/api/models";
import { useSession } from "@/lib/auth/useSession";
import { useTheme } from "@/lib/theme/ThemeProvider";
import { formatPercent } from "@/lib/utils";

export default function SettingsPage() {
  const { user, refresh } = useSession();
  const { theme, setTheme } = useTheme();
  const activeModel = useSWR("settings-active-model", () => getActiveModelDetail());
  const { showToast } = useToast();
  const router = useRouter();
  const [savingTheme, setSavingTheme] = useState(false);

  async function handleThemeChange(next: "light" | "dark") {
    setSavingTheme(true);
    setTheme(next);
    await refresh();
    setSavingTheme(false);
    showToast("Theme preference saved.", "success");
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Settings</h1>
        <p className="text-sm text-text-muted">Manage your profile, organization, and preferences.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
        </CardHeader>
        {!user ? (
          <p className="text-sm text-text-muted">Loading…</p>
        ) : (
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs text-text-muted">Full name</dt>
              <dd className="text-sm font-medium text-text-primary">{user.full_name}</dd>
            </div>
            <div>
              <dt className="text-xs text-text-muted">Email</dt>
              <dd className="text-sm font-medium text-text-primary">{user.email}</dd>
              <dd className="mt-0.5 text-xs text-text-muted">Email changes aren&apos;t supported yet.</dd>
            </div>
            <div>
              <dt className="text-xs text-text-muted">Organization</dt>
              <dd className="text-sm font-medium text-text-primary">{user.organization_name ?? `Org #${user.organization_id}`}</dd>
            </div>
          </dl>
        )}
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
        </CardHeader>
        <div className="flex items-center gap-3">
          <Button
            size="sm"
            variant={theme === "light" ? "primary" : "secondary"}
            onClick={() => handleThemeChange("light")}
            loading={savingTheme && theme === "light"}
          >
            Light
          </Button>
          <Button
            size="sm"
            variant={theme === "dark" ? "primary" : "secondary"}
            onClick={() => handleThemeChange("dark")}
            loading={savingTheme && theme === "dark"}
          >
            Dark
          </Button>
        </div>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Risk Thresholds</CardTitle>
        </CardHeader>
        {!activeModel.data ? (
          <p className="text-sm text-text-muted">Loading…</p>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap gap-2">
              <Badge tone="success">Low: below {formatPercent(activeModel.data.metadata.risk_thresholds?.low_max, 0)}</Badge>
              <Badge tone="warning">
                Medium: {formatPercent(activeModel.data.metadata.risk_thresholds?.low_max, 0)}–
                {formatPercent(activeModel.data.metadata.risk_thresholds?.medium_max, 0)}
              </Badge>
              <Badge tone="danger">High: above {formatPercent(activeModel.data.metadata.risk_thresholds?.medium_max, 0)}</Badge>
            </div>
            <p className="text-xs text-text-muted">Customizing thresholds — coming soon.</p>
          </div>
        )}
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Onboarding</CardTitle>
        </CardHeader>
        <Button size="sm" variant="secondary" onClick={() => router.push("/dashboard?tour=replay")}>
          Replay walkthrough
        </Button>
      </Card>
    </div>
  );
}
