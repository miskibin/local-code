"use client";
import { useEffect, useState } from "react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL_BASE ?? "http://localhost:8000";

type Tool = { name: string; enabled: boolean; description: string };

export default function SettingsPage() {
  const [tools, setTools] = useState<Tool[]>([]);

  useEffect(() => {
    fetch(`${BACKEND}/tools`).then((r) => r.json()).then(setTools);
  }, []);

  async function toggle(name: string, enabled: boolean) {
    setTools((p) => p.map((t) => (t.name === name ? { ...t, enabled } : t)));
    await fetch(`${BACKEND}/tools/${name}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
  }

  return (
    <main className="mx-auto max-w-xl p-8 space-y-6">
      <h1 className="text-2xl font-semibold">Settings</h1>
      <section className="space-y-3">
        <h2 className="text-lg font-medium">Tools</h2>
        {tools.map((t) => (
          <div key={t.name} className="flex items-center justify-between gap-4">
            <Label htmlFor={t.name} className="flex flex-col items-start">
              <span>{t.name}</span>
              {t.description && (
                <span className="text-xs text-muted-foreground">{t.description}</span>
              )}
            </Label>
            <Switch
              id={t.name}
              checked={t.enabled}
              onCheckedChange={(v) => toggle(t.name, v)}
            />
          </div>
        ))}
      </section>
    </main>
  );
}
