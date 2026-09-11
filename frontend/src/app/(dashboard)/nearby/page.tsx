"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { emergencyApi } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { Building2, FlaskConical, Hospital, MapPin, Pill } from "lucide-react";
import { useState } from "react";

const TYPES = [
  { key: "hospital", label: "Hospitals", icon: Hospital },
  { key: "clinic", label: "Clinics", icon: Building2 },
  { key: "lab", label: "Labs", icon: FlaskConical },
  { key: "pharmacy", label: "Pharmacies", icon: Pill },
];

export default function NearbyPage() {
  const [type, setType] = useState("hospital");

  const { data } = useQuery({
    queryKey: ["nearby", type],
    queryFn: () => emergencyApi.nearby({ service_type: type }).then((r) => r.data),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Nearby Services</h1>
        <p className="text-slate-500">Find hospitals, clinics, labs, and pharmacies near you</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {TYPES.map((t) => (
          <button
            key={t.key}
            onClick={() => setType(t.key)}
            className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
              type === t.key ? "bg-teal-600 text-white" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
            }`}
          >
            <t.icon className="h-4 w-4" /> {t.label}
          </button>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {data?.services?.map((s: { name: string; type: string; distance_km: number; rating: number }, i: number) => (
          <Card key={i}>
            <CardContent className="flex items-center justify-between p-4">
              <div className="flex items-center gap-3">
                <MapPin className="h-5 w-5 text-teal-500" />
                <div>
                  <p className="font-medium">{s.name}</p>
                  <p className="text-sm text-slate-500">{s.distance_km} km away</p>
                </div>
              </div>
              <span className="text-sm font-medium text-amber-600">★ {s.rating}</span>
            </CardContent>
          </Card>
        ))}
      </div>

      {data?.maps_url && (
        <a href={data.maps_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 text-sm text-teal-600 hover:underline">
          <MapPin className="h-4 w-4" /> Open in Google Maps
        </a>
      )}
    </div>
  );
}
