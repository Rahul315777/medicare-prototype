"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { medicalApi } from "@/lib/api";
import { useMutation } from "@tanstack/react-query";
import { Clock, Loader2, Pill, Upload } from "lucide-react";
import { useRef, useState } from "react";

export default function PrescriptionsPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [result, setResult] = useState<{ medicines: { name: string; dosage: string; timing: string; duration_days: number }[]; doctor_name: string } | null>(null);

  const scanMutation = useMutation({
    mutationFn: (file: File) => medicalApi.scanPrescription(file),
    onSuccess: (res) => setResult(res.data),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Prescription Scanner</h1>
        <p className="text-slate-500">Upload prescription photos to extract medicines and set reminders</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Scan Prescription</CardTitle>
          <CardDescription>OCR-powered medicine extraction</CardDescription>
        </CardHeader>
        <CardContent>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files?.[0] && scanMutation.mutate(e.target.files[0])} />
          <Button onClick={() => fileRef.current?.click()} disabled={scanMutation.isPending} className="gap-2">
            {scanMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            Upload Prescription
          </Button>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Extracted Medicines</CardTitle>
            <CardDescription>Prescribed by {result.doctor_name || "Doctor"}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {result.medicines?.map((med, i) => (
              <div key={i} className="flex items-center justify-between rounded-xl bg-slate-50 p-4 dark:bg-slate-800/50">
                <div className="flex items-center gap-3">
                  <Pill className="h-5 w-5 text-purple-500" />
                  <div>
                    <p className="font-medium">{med.name}</p>
                    <p className="text-sm text-slate-500">{med.dosage}</p>
                  </div>
                </div>
                <div className="text-right text-sm">
                  <p className="flex items-center gap-1 text-slate-500"><Clock className="h-3 w-3" /> {med.timing}</p>
                  <p className="text-xs text-teal-600">{med.duration_days} days • Reminder created</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
