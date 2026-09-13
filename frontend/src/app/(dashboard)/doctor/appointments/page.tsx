"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { doctorApi } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ClipboardEdit,
  FileText,
  MessageSquare,
  Pill,
  ShieldAlert,
  User,
} from "lucide-react";
import { useState } from "react";

interface Patient {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
}

interface DoctorAppointment {
  id: string;
  scheduled_at: string;
  status: string;
  notes: string | null;
  call_summary: Record<string, unknown> | null;
  patient: Patient;
  // Doctor Portal additions
  clinical_session_status: string | null;
  history_completed: boolean;
  has_red_flags: boolean;
  highest_red_flag_severity: string | null;
  red_flag_count: number;
  summary_available: boolean;
}

const SEVERITY_STYLES: Record<string, string> = {
  critical: "bg-red-100 text-red-800 border-red-300 dark:bg-red-950/40 dark:text-red-300 dark:border-red-900",
  high: "bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-950/40 dark:text-orange-300 dark:border-orange-900",
  moderate: "bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900",
  low: "bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700",
};

function SeverityBadge({ severity }: { severity: string }) {
  const style = SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.low;
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${style}`}>
      {severity}
    </span>
  );
}

export default function DoctorAppointmentsPage() {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data: appointments, isLoading, error } = useQuery({
    queryKey: ["doctor-appointments"],
    queryFn: () => doctorApi.myAppointments().then((r) => r.data as DoctorAppointment[]),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Doctor Portal — My Appointments</h1>
        <p className="text-slate-500">Real patient data: profile, chat history, OCR reports, and AI clinical summaries</p>
      </div>

      {isLoading && (
        <div className="flex h-40 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-500 border-t-transparent" />
        </div>
      )}

      {error != null && (
        <div className="rounded-xl bg-red-50 dark:bg-red-950/30 p-4 text-sm text-red-700 dark:text-red-400 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4" />
          Could not load appointments. This page requires a doctor account (role=doctor, linked to a Doctor record).
        </div>
      )}

      {appointments?.length === 0 && (
        <p className="text-sm text-slate-500">No appointments booked with you yet.</p>
      )}

      <div className="space-y-3">
        {appointments?.map((appt) => (
          <Card key={appt.id} className={appt.has_red_flags ? "border-red-300 dark:border-red-900" : undefined}>
            <CardHeader
              className="cursor-pointer flex flex-row items-center justify-between"
              onClick={() => setExpandedId(expandedId === appt.id ? null : appt.id)}
            >
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <User className="h-4 w-4 text-teal-600" /> {appt.patient.full_name}
                  {appt.has_red_flags && appt.highest_red_flag_severity && (
                    <SeverityBadge severity={appt.highest_red_flag_severity} />
                  )}
                </CardTitle>
                <p className="text-sm text-slate-500 flex items-center gap-2 mt-1 flex-wrap">
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3.5 w-3.5" /> {new Date(appt.scheduled_at).toLocaleString()} · {appt.status}
                  </span>
                  <span>
                    · Clinical history:{" "}
                    {appt.clinical_session_status
                      ? `${appt.clinical_session_status}${appt.history_completed ? " (complete)" : ""}`
                      : "not started"}
                  </span>
                  {appt.has_red_flags && (
                    <span className="flex items-center gap-1 text-red-600 dark:text-red-400 font-medium">
                      <ShieldAlert className="h-3.5 w-3.5" /> {appt.red_flag_count} clinical alert
                      {appt.red_flag_count > 1 ? "s" : ""} detected
                    </span>
                  )}
                  {appt.summary_available && <span>· AI summary ready</span>}
                </p>
              </div>
              {expandedId === appt.id ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
            </CardHeader>

            {expandedId === appt.id && (
              <CardContent>
                <PatientSummaryPanel appointmentId={appt.id} />
              </CardContent>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

function PatientSummaryPanel({ appointmentId }: { appointmentId: string }) {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["doctor-patient-summary", appointmentId],
    queryFn: () => doctorApi.getPatientSummary(appointmentId).then((r) => r.data),
  });

  const acknowledgeMutation = useMutation({
    mutationFn: (alertId: string) => doctorApi.acknowledgeRedFlag(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["doctor-patient-summary", appointmentId] });
      queryClient.invalidateQueries({ queryKey: ["doctor-appointments"] });
    },
  });

  if (isLoading) {
    return <p className="text-sm text-slate-500">Loading patient summary...</p>;
  }
  if (error) {
    return <p className="text-sm text-red-600">Failed to load patient summary.</p>;
  }

  const summary = data.call_summary as Record<string, any> | null;
  const doctorReview = summary?.doctor_review as Record<string, any> | undefined;
  const ctx = data.patient_context;

  // Flatten red flags across this patient's recent clinical sessions for a
  // single, prominent "Clinical Alerts" section — this is decision support,
  // never a diagnosis.
  const allRedFlags = (ctx.clinical_sessions ?? []).flatMap((s: any) =>
    (s.red_flags ?? []).map((rf: any) => ({ ...rf, session_id: s.session_id }))
  );

  return (
    <div className="space-y-6 border-t border-slate-200 dark:border-slate-800 pt-4">
      {allRedFlags.length > 0 && (
        <section className="rounded-xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/20 p-4">
          <h3 className="font-semibold text-sm mb-3 flex items-center gap-2 text-red-800 dark:text-red-300">
            <ShieldAlert className="h-4 w-4" /> Clinical Alerts Detected (decision support — not a diagnosis)
          </h3>
          <div className="space-y-3">
            {allRedFlags.map((rf: any) => (
              <div
                key={rf.alert_id}
                className="rounded-lg bg-white dark:bg-slate-900 border border-red-100 dark:border-red-900/50 p-3 text-sm space-y-1"
              >
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={rf.severity} />
                    <span className="font-medium">{(rf.detected_symptoms ?? []).join(", ") || "Symptoms not specified"}</span>
                  </div>
                  {rf.acknowledged ? (
                    <span className="flex items-center gap-1 text-xs text-emerald-700 dark:text-emerald-400">
                      <CheckCircle2 className="h-3.5 w-3.5" /> Acknowledged
                    </span>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={acknowledgeMutation.isPending}
                      onClick={() => acknowledgeMutation.mutate(rf.alert_id)}
                    >
                      Acknowledge
                    </Button>
                  )}
                </div>
                <p className="text-slate-600 dark:text-slate-400">{rf.reason}</p>
                <p className="text-xs text-slate-500">
                  Recommended action: {rf.recommended_action} · Source: {rf.source} ·{" "}
                  {new Date(rf.created_at).toLocaleString()}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <h3 className="font-semibold text-sm mb-2 flex items-center gap-2">
          <FileText className="h-4 w-4 text-teal-600" /> AI Clinical Summary
        </h3>
        {summary ? (
          <div className="grid sm:grid-cols-2 gap-3 text-sm bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4">
            <div><span className="font-medium">Chief complaints:</span> {String(summary.chief_complaints)}</div>
            <div><span className="font-medium">Symptoms:</span> {(summary.symptoms as string[])?.join(", ") || "Not provided"}</div>
            <div><span className="font-medium">Medical history:</span> {String(summary.medical_history)}</div>
            <div><span className="font-medium">Medications:</span> {(summary.medications as string[])?.join(", ") || "Not provided"}</div>
            <div><span className="font-medium">Allergies:</span> {String(summary.allergies)}</div>
            <div><span className="font-medium">Reports:</span> {String(summary.reports)}</div>
            <div className="sm:col-span-2"><span className="font-medium">Important findings:</span> {String(summary.important_findings)}</div>
          </div>
        ) : (
          <p className="text-sm text-slate-500">
            No summary generated yet for this appointment. The patient can generate one from their side, or the doctor
            review form below will generate one automatically on first save.
          </p>
        )}
      </section>

      <DoctorReviewForm appointmentId={appointmentId} existingReview={doctorReview} />

      <section>
        <h3 className="font-semibold text-sm mb-2 flex items-center gap-2">
          <User className="h-4 w-4 text-teal-600" /> Profile
        </h3>
        <div className="grid sm:grid-cols-3 gap-3 text-sm">
          <div><span className="font-medium">Age:</span> {ctx.patient.age}</div>
          <div><span className="font-medium">Gender:</span> {ctx.patient.gender}</div>
          <div><span className="font-medium">Blood group:</span> {ctx.patient.blood_group}</div>
          <div className="sm:col-span-3"><span className="font-medium">Allergies:</span> {ctx.patient.known_allergies?.join(", ") || "unknown/not provided"}</div>
          <div className="sm:col-span-3"><span className="font-medium">Medical history:</span> {ctx.patient.known_medical_history?.join(", ") || "unknown/not provided"}</div>
        </div>
      </section>

      <section>
        <h3 className="font-semibold text-sm mb-2 flex items-center gap-2">
          <ClipboardEdit className="h-4 w-4 text-teal-600" /> AI Pre-Consultation Clinical Interview
        </h3>
        {ctx.clinical_sessions?.length ? (
          <div className="space-y-3 text-sm">
            {ctx.clinical_sessions.map((s: any) => (
              <div key={s.session_id} className="rounded-lg bg-slate-50 dark:bg-slate-800/50 p-3">
                <p className="font-medium">
                  {s.chief_complaint} <span className="text-slate-500 font-normal">({s.status})</span>
                </p>
                <div className="mt-1 grid sm:grid-cols-2 gap-x-4 gap-y-0.5 text-slate-600 dark:text-slate-400">
                  {Object.entries(s.collected_fields ?? {}).map(([field, value]) => (
                    <div key={field}>
                      <span className="font-medium">{field}:</span> {String(value)}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">unknown/not provided</p>
        )}
      </section>

      <section>
        <h3 className="font-semibold text-sm mb-2 flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-teal-600" /> Recent Chat / Symptoms
        </h3>
        {ctx.recent_chats?.length ? (
          <div className="space-y-2 max-h-56 overflow-y-auto text-sm">
            {ctx.recent_chats.flatMap((s: any) => s.messages).map((m: any, i: number) => (
              <p key={i}><span className="font-medium">{m.role}:</span> {m.content}</p>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">unknown/not provided</p>
        )}
      </section>

      <section>
        <h3 className="font-semibold text-sm mb-2 flex items-center gap-2">
          <FileText className="h-4 w-4 text-teal-600" /> Uploaded Reports (OCR findings)
        </h3>
        {ctx.reports?.length ? (
          <div className="space-y-2 text-sm">
            {ctx.reports.map((r: any) => (
              <div key={r.report_id} className="rounded-lg bg-slate-50 dark:bg-slate-800/50 p-3">
                <p className="font-medium">{r.title} ({r.report_type}) — risk: {r.risk_level}</p>
                <p className="text-slate-500">{r.findings?.summary || "No summary available"}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">unknown/not provided</p>
        )}
      </section>

      <section>
        <h3 className="font-semibold text-sm mb-2 flex items-center gap-2">
          <Pill className="h-4 w-4 text-teal-600" /> Prescriptions
        </h3>
        {ctx.prescriptions?.length ? (
          <div className="space-y-1 text-sm">
            {ctx.prescriptions.map((p: any) => (
              <p key={p.prescription_id}>
                From {p.doctor_name}: {p.medicines?.map((m: any) => m.name).join(", ") || "unknown/not provided"}
              </p>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">unknown/not provided</p>
        )}
      </section>
    </div>
  );
}

function DoctorReviewForm({
  appointmentId,
  existingReview,
}: {
  appointmentId: string;
  existingReview?: Record<string, any>;
}) {
  const queryClient = useQueryClient();
  const [chiefComplaints, setChiefComplaints] = useState(existingReview?.chief_complaints ?? "");
  const [medicalHistory, setMedicalHistory] = useState(existingReview?.medical_history ?? "");
  const [importantFindings, setImportantFindings] = useState(existingReview?.important_findings ?? "");
  const [doctorNotes, setDoctorNotes] = useState(existingReview?.doctor_notes ?? "");

  const reviewMutation = useMutation({
    mutationFn: () =>
      doctorApi.reviewSummary(appointmentId, {
        chief_complaints: chiefComplaints || null,
        medical_history: medicalHistory || null,
        important_findings: importantFindings || null,
        doctor_notes: doctorNotes || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["doctor-patient-summary", appointmentId] });
      queryClient.invalidateQueries({ queryKey: ["doctor-appointments"] });
    },
  });

  return (
    <section className="rounded-xl border border-teal-200 dark:border-teal-900 bg-teal-50/50 dark:bg-teal-950/10 p-4">
      <h3 className="font-semibold text-sm mb-1 flex items-center gap-2 text-teal-800 dark:text-teal-300">
        <ClipboardEdit className="h-4 w-4" /> Doctor Review
      </h3>
      <p className="text-xs text-slate-500 mb-3">
        Corrections here are stored separately from the AI-generated summary above — the original AI output is
        never overwritten, so what the AI inferred and what you confirmed both stay visible.
      </p>
      <div className="space-y-2">
        <Input
          placeholder="Corrected chief complaint (leave blank to keep AI value)"
          value={chiefComplaints}
          onChange={(e) => setChiefComplaints(e.target.value)}
        />
        <Input
          placeholder="Corrected medical history"
          value={medicalHistory}
          onChange={(e) => setMedicalHistory(e.target.value)}
        />
        <Input
          placeholder="Corrected important findings"
          value={importantFindings}
          onChange={(e) => setImportantFindings(e.target.value)}
        />
        <Input
          placeholder="Doctor's notes"
          value={doctorNotes}
          onChange={(e) => setDoctorNotes(e.target.value)}
        />
        <div className="flex items-center gap-3">
          <Button size="sm" disabled={reviewMutation.isPending} onClick={() => reviewMutation.mutate()}>
            Save review
          </Button>
          {reviewMutation.isSuccess && (
            <span className="text-xs text-emerald-700 dark:text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="h-3.5 w-3.5" /> Saved
            </span>
          )}
          {reviewMutation.isError && <span className="text-xs text-red-600">Failed to save review.</span>}
        </div>
        {existingReview?.reviewed && (
          <p className="text-xs text-slate-500">Last reviewed {new Date(existingReview.reviewed_at).toLocaleString()}</p>
        )}
      </div>
    </section>
  );
}
