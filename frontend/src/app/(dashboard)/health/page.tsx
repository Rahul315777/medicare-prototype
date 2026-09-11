"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { dashboardApi, medicalApi } from "@/lib/api";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Activity, Droplets, Heart, Loader2, Moon, Upload, Weight } from "lucide-react";
import { useRef, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const METRIC_TYPES = [
  { type: "weight", label: "Weight", unit: "kg", icon: Weight },
  { type: "sugar", label: "Blood Sugar", unit: "mg/dL", icon: Droplets },
  { type: "systolic_bp", label: "Blood Pressure", unit: "mmHg", icon: Heart },
  { type: "heart_rate", label: "Heart Rate", unit: "bpm", icon: Activity },
  { type: "sleep", label: "Sleep", unit: "hours", icon: Moon },
];

export default function HealthPage() {
  const [metric, setMetric] = useState({ type: "weight", value: "", unit: "kg" });

  const { data: metrics, refetch } = useQuery({
    queryKey: ["health-metrics"],
    queryFn: () => dashboardApi.getMetrics().then((r) => r.data),
  });

  const { data: risks } = useQuery({
    queryKey: ["risk-prediction"],
    queryFn: () => medicalApi.riskPrediction().then((r) => r.data),
  });

  const addMutation = useMutation({
    mutationFn: () =>
      dashboardApi.addMetric({
        metric_type: metric.type,
        value: parseFloat(metric.value),
        unit: metric.unit,
      }),
    onSuccess: () => {
      refetch();
      setMetric({ ...metric, value: "" });
    },
  });

  const chartData = (metrics || [])
    .filter((m: { metric_type: string }) => m.metric_type === "weight")
    .slice(0, 10)
    .reverse()
    .map((m: { recorded_at: string; value: number }) => ({
      date: new Date(m.recorded_at).toLocaleDateString("en-IN", { month: "short", day: "numeric" }),
      value: m.value,
    }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Health Tracker</h1>
        <p className="text-slate-500">Monitor your vitals and health trends</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {risks && [
          { label: "Diabetes Risk", value: risks.diabetes_risk, color: "text-amber-600" },
          { label: "Heart Disease Risk", value: risks.heart_disease_risk, color: "text-red-600" },
          { label: "Hypertension Risk", value: risks.hypertension_risk, color: "text-orange-600" },
        ].map((r) => (
          <Card key={r.label}>
            <CardContent className="p-6 text-center">
              <p className="text-sm text-slate-500">{r.label}</p>
              <p className={`text-3xl font-bold ${r.color}`}>{r.value}%</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Weight Trend</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={chartData.length ? chartData : [{ date: "Today", value: 70 }]}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Area type="monotone" dataKey="value" stroke="#0d9488" fill="#0d9488" fillOpacity={0.2} />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Log Health Metric</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-4">
          <div className="space-y-2">
            <Label>Metric</Label>
            <select
              value={metric.type}
              onChange={(e) => {
                const m = METRIC_TYPES.find((t) => t.type === e.target.value);
                setMetric({ type: e.target.value, value: metric.value, unit: m?.unit || "kg" });
              }}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
            >
              {METRIC_TYPES.map((m) => (
                <option key={m.type} value={m.type}>{m.label}</option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <Label>Value</Label>
            <Input
              type="number"
              value={metric.value}
              onChange={(e) => setMetric({ ...metric, value: e.target.value })}
              placeholder="Enter value"
            />
          </div>
          <div className="flex items-end">
            <Button onClick={() => addMutation.mutate()} disabled={!metric.value || addMutation.isPending}>
              {addMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
