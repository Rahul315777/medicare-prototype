"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { medicalApi } from "@/lib/api";
import { getRiskColor } from "@/lib/utils";
import { useMutation, useQuery } from "@tanstack/react-query";
import { FileText, Loader2, Upload, Bot, MapPin, Star, CalendarPlus } from "lucide-react";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation"; // 👈 Router add kiya hai

export default function ReportsPage() {
  const router = useRouter(); // 👈 Page redirect karne ke liye
  const [reportType, setReportType] = useState("blood");
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: reports, refetch } = useQuery({
    queryKey: ["reports"],
    queryFn: () => medicalApi.listReports().then((r) => r.data),
  });

  const analyzeMutation = useMutation({
    mutationFn: (file: File) => medicalApi.analyzeReport(file, reportType, file.name),
    onSuccess: () => refetch(),
  });

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) analyzeMutation.mutate(file);
  };

  const analysisData = analyzeMutation.data?.data?.analysis || analyzeMutation.data?.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Medical Report Analyzer</h1>
        <p className="text-slate-500">Upload PDF or images for AI-powered analysis</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Upload Report</CardTitle>
          <CardDescription>Supports PDF, blood reports, CBC, MRI, X-ray, ECG</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <select
            value={reportType}
            onChange={(e) => setReportType(e.target.value)}
            className="rounded-xl border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
          >
            <option value="blood">Blood Report</option>
            <option value="cbc">CBC</option>
            <option value="mri">MRI</option>
            <option value="xray">X-ray</option>
            <option value="ecg">ECG</option>
          </select>
          <input ref={fileRef} type="file" accept=".pdf,image/*" className="hidden" onChange={handleUpload} />
          <Button onClick={() => fileRef.current?.click()} disabled={analyzeMutation.isPending} className="gap-2">
            {analyzeMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            {analyzeMutation.isPending ? "AI is Reading Your Report..." : "Upload & Analyze"}
          </Button>
        </CardContent>
      </Card>

      {/* SMART AI ANALYSIS DISPLAY BOX */}
      {analysisData && (
        <Card className="border-teal-500/30 bg-teal-50/10 dark:bg-slate-900/50">
          <CardHeader className="flex flex-row items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-teal-100 dark:bg-teal-900">
              <Bot className="h-5 w-5 text-teal-600" />
            </div>
            <div>
              <CardTitle>AI Doctor Report Analysis</CardTitle>
              <CardDescription>Detailed insights powered by Groq Llama-3 Medical AI</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            
            {/* 1. Prints Summary */}
            {(analysisData.summary || analysisData.explanation || typeof analysisData === "string") && (
              <div className="rounded-xl bg-slate-50 p-4 text-sm leading-relaxed dark:bg-slate-800">
                <p className="whitespace-pre-wrap font-medium">
                  {analysisData.summary || analysisData.explanation || analysisData}
                </p>
              </div>
            )}

            {/* 2. Prints Values Table */}
            {analysisData.values && Array.isArray(analysisData.values) && analysisData.values.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Extracted Values</h3>
                {analysisData.values.map(
                  (v: { name: string; value: number | string; unit?: string; status?: string; reference_range?: string }, i: number) => (
                    <div key={i} className="flex items-center justify-between rounded-xl bg-slate-50 p-3 dark:bg-slate-800/50">
                      <div>
                        <p className="font-medium">{v.name}</p>
                        {v.reference_range && <p className="text-xs text-slate-500">Ref: {v.reference_range}</p>}
                      </div>
                      <div className="text-right">
                        <p className="font-semibold">
                          {v.value} {v.unit || ""}
                        </p>
                        {v.status && (
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${getRiskColor(
                              v.status === "high" ? "high" : v.status === "low" ? "moderate" : "low"
                            )}`}
                          >
                            {v.status}
                          </span>
                        )}
                      </div>
                    </div>
                  )
                )}
              </div>
            )}

            {/* 3. DOCTORS FROM GOOGLE MAPS WITH BOOKING BUTTON */}
            {analysisData.real_doctors && Array.isArray(analysisData.real_doctors) && analysisData.real_doctors.length > 0 && (
              <div className="space-y-3 pt-4 border-t border-slate-200 dark:border-slate-800">
                <div>
                  <h3 className="text-sm font-semibold text-teal-600 dark:text-teal-400">
                    👨‍⚕️ Top {analysisData.recommended_specialty || "Specialist"}s Near You
                  </h3>
                  <p className="text-xs text-slate-500">Sourced directly from Google Maps</p>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {analysisData.real_doctors.map((doctor: any, i: number) => (
                    <div key={i} className="flex flex-col justify-between rounded-xl bg-slate-50 p-4 border border-slate-100 dark:bg-slate-800 dark:border-slate-700 shadow-sm hover:shadow-md transition-shadow">
                      <div>
                        <h4 className="font-bold text-slate-900 dark:text-white mb-1">{doctor.name}</h4>
                        <div className="flex items-start gap-1 text-xs text-slate-500 mb-3">
                          <MapPin className="h-3 w-3 mt-0.5 shrink-0" />
                          <span className="line-clamp-2">{doctor.address}</span>
                        </div>
                      </div>
                      <div className="flex items-center justify-between mt-2 pt-3 border-t border-slate-200 dark:border-slate-700">
                        <div className="flex items-center gap-1 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-500 px-2 py-1 rounded-md text-xs font-bold">
                          <Star className="h-3 w-3 fill-current" />
                          {doctor.rating}
                        </div>
                        {/* 👈 NAYA BOOK NOW BUTTON */}
                        <Button size="sm" onClick={() => router.push('/appointments')} className="h-8 gap-1 text-xs bg-teal-600 hover:bg-teal-700 text-white">
                          <CalendarPlus className="h-3 w-3" />
                          Book Now
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <p className="text-center text-xs text-slate-400 border-t pt-3 mt-4">
              Note: AI analysis is for educational purposes. Always consult a doctor for clinical diagnosis.
            </p>
          </CardContent>
        </Card>
      )}

      {/* RECENT REPORTS SECTION */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">Recent Reports</h2>
        {reports?.length ? (
          reports.map((r: { id: string; title: string; report_type: string; risk_level: string; created_at: string }) => (
            <Card key={r.id}>
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-teal-500" />
                  <div>
                    <p className="font-medium">{r.title}</p>
                    <p className="text-sm text-slate-500">{r.report_type}</p>
                  </div>
                </div>
                <span className={`rounded-full px-3 py-1 text-xs font-medium ${getRiskColor(r.risk_level || "low")}`}>
                  {r.risk_level || "low"} risk
                </span>
              </CardContent>
            </Card>
          ))
        ) : (
          <p className="text-sm text-slate-500">No reports yet. Upload your first report above.</p>
        )}
      </div>
    </div>
  );
}