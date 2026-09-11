"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { medicalApi } from "@/lib/api";
import { useState } from "react";

export default function KnowledgePage() {
  const [tab, setTab] = useState<"medicine" | "disease">("medicine");
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = tab === "medicine"
        ? await medicalApi.getMedicine(query)
        : await medicalApi.getDisease(query);
      setResult(res.data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Medical Knowledge Base</h1>
        <p className="text-slate-500">Search medicines and diseases</p>
      </div>

      <div className="flex gap-2">
        <Button variant={tab === "medicine" ? "default" : "outline"} onClick={() => { setTab("medicine"); setResult(null); }}>Medicines</Button>
        <Button variant={tab === "disease" ? "default" : "outline"} onClick={() => { setTab("disease"); setResult(null); }}>Diseases</Button>
      </div>

      <div className="flex gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
          placeholder={tab === "medicine" ? "Search medicine (e.g. Paracetamol)..." : "Search disease (e.g. Diabetes)..."}
          className="flex-1"
        />
        <Button onClick={search} disabled={loading}>{loading ? "..." : "Search"}</Button>
      </div>

      {result && (
        <Card>
          <CardHeader><CardTitle>{String(result.name)}</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {Object.entries(result).filter(([k]) => k !== "name").map(([key, value]) => (
              <div key={key}>
                <p className="text-sm font-medium capitalize text-teal-600">{key.replace(/_/g, " ")}</p>
                {Array.isArray(value) ? (
                  <ul className="mt-1 list-inside list-disc text-sm text-slate-600 dark:text-slate-400">
                    {value.map((v, i) => <li key={i}>{String(v)}</li>)}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-600 dark:text-slate-400">{String(value)}</p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
