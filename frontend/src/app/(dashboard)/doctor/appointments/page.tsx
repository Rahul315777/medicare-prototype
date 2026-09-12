"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { doctorApi } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Calendar, ChevronDown, ChevronUp, FileText, MessageSquare, Pill, User } from "lucide-react";
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
          <Card key={appt.id}>
            <CardHeader
              className="cursor-pointer flex flex-row items-center justify-between"
              onClick={() => setExpandedId(expandedId === appt.id ? null : appt.id)}
            >
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <User className="h-4 w-4 text-teal-600" /> {appt.patient.full_name}
                </CardTitle>
                <p className="text-sm text-slate-500 flex items-center gap-1 mt-1">
                  <Calendar className="h-3.5 w-3.5" /> {new Date(appt.scheduled_at).toLocaleString()} · {appt.status}
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
  const { data, isLoading, error } = useQuery({
    queryKey: ["doctor-patient-summary", appointmentId],
    queryFn: () => doctorApi.getPatientSummary(appointmentId).then((r) => r.data),
  });

  if (isLoading) {
    return <p className="text-sm text-slate-500">Loading patient summary...</p>;
  }
  if (error) {
    return <p className="text-sm text-red-600">Failed to load patient summary.</p>;
  }

  const summary = data.call_summary as Record<string, any> | null;
  const ctx = data.patient_context;

  return (
    <div className="space-y-6 border-t border-slate-200 dark:border-slate-800 pt-4">
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
            No summary generated yet for this appointment. The patient can generate one from their side, or trigger
            <code className="mx-1 rounded bg-slate-100 dark:bg-slate-800 px-1">POST /appointments/{"{id}"}/summary</code>
            manually for this demo.
          </p>
        )}
      </section>

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