"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Activity, AlertTriangle, Bell, Bot, Calendar, ChevronRight, FileText, Heart,
  Pill, RefreshCw, Sparkles, Stethoscope, TrendingUp, Upload
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis } from "recharts"; 

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { dashboardApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

// ==========================================
// Strict TypeScript Interfaces
// ==========================================
interface Doctor {
  id: string;
  name: string;
  specialty: string;
  rating: number;
}

interface Appointment {
  id: string;
  scheduled_at: string;
  doctor?: Doctor;
}

interface Reminder {
  id: string;
  medicine_name: string;
  dosage: string;
  timing: string;
}

interface Report {
  id: string;
  title: string;
  created_at: string;
}

interface DashboardResponse {
  health_score: number;
  score_trend: string;
  health_trend_data?: { day: string; score: number }[];
  upcoming_appointments: Appointment[];
  medicine_reminders: Reminder[];
  recent_reports: Report[];
  daily_tip: string;
  recommended_doctors: Doctor[];
}

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } };
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } };

export default function DashboardPage() {
  const { user } = useAuthStore();
  const [greeting, setGreeting] = useState("Welcome");

  useEffect(() => {
    const hour = new Date().getHours();
    if (hour < 12) setGreeting("Good Morning");
    else if (hour < 18) setGreeting("Good Afternoon");
    else setGreeting("Good Evening");
  }, []);

  // ==========================================
  // Optimized React Query
  // ==========================================
  const { data, isLoading, isError, refetch, isRefetching } = useQuery<DashboardResponse>({
    queryKey: ["dashboard"],
    queryFn: () => dashboardApi.get().then((r) => r.data),
    staleTime: 5 * 60 * 1000, // Data remains fresh for 5 mins
    refetchOnWindowFocus: false, 
    retry: 2,
  });

  if (isError) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center text-center px-4">
        <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-full mb-4">
          <AlertTriangle className="h-10 w-10 text-red-500" />
        </div>
        <h3 className="text-xl font-bold mb-2">Unable to load dashboard</h3>
        <p className="text-slate-500 mb-6">There was a problem fetching your health data. Please try again.</p>
        <Button onClick={() => refetch()} className="gap-2" disabled={isRefetching}>
          <RefreshCw className={`h-4 w-4 ${isRefetching ? "animate-spin" : ""}`} />
          Retry Connection
        </Button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <RefreshCw className="h-8 w-8 animate-spin text-teal-600" />
          <p className="text-slate-500 font-medium">Loading your health dashboard...</p>
        </div>
      </div>
    ); 
  }

  const dashboard = data || {
    health_score: 82,
    score_trend: "+4",
    upcoming_appointments: [],
    medicine_reminders: [],
    recent_reports: [],
    daily_tip: "Drinking a glass of water right after waking up helps jumpstart your digestion.",
    recommended_doctors: [],
    health_trend_data: [
      { day: "Mon", score: 65 }, { day: "Tue", score: 68 }, { day: "Wed", score: 72 }, 
      { day: "Thu", score: 71 }, { day: "Fri", score: 75 }, { day: "Sat", score: 78 }, { day: "Sun", score: 82 }
    ]
  };

  const getHealthStatus = (score: number) => {
    if (score >= 90) return { color: "text-green-500", bg: "bg-green-500", light: "bg-green-500/10", text: "Excellent" };
    if (score >= 70) return { color: "text-blue-500", bg: "bg-blue-500", light: "bg-blue-500/10", text: "Good" };
    if (score >= 50) return { color: "text-amber-500", bg: "bg-amber-500", light: "bg-amber-500/10", text: "Fair" };
    return { color: "text-red-500", bg: "bg-red-500", light: "bg-red-500/10", text: "Needs Attention" };
  };

  const healthStatus = getHealthStatus(dashboard.health_score);
  const firstName = user?.full_name?.split(" ")[0] || "User";

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-8 pb-10">
      
      {/* HEADER */}
      <motion.div variants={item} className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
            {greeting}, {firstName} 👋
          </h1>
          <p className="text-slate-500">Here&apos;s your health overview for today.</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="icon" onClick={() => refetch()} disabled={isRefetching} title="Refresh Data">
            <RefreshCw className={`h-4 w-4 ${isRefetching ? "animate-spin text-teal-600" : ""}`} />
          </Button>
          <Button variant="outline" size="icon" className="relative">
            <Bell className="h-4 w-4" />
            <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-red-500 ring-2 ring-white dark:ring-slate-900"></span>
          </Button>
        </div>
      </motion.div>

      {/* QUICK STATS BANNER */}
      <motion.div variants={item} className="grid gap-6 md:grid-cols-3">
        {/* Health Score Card */}
        <Card className="shadow-md border-slate-200 dark:border-slate-800 bg-gradient-to-br from-teal-500 to-emerald-600 text-white">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-white text-lg">Overall Health Score</CardTitle>
            <Heart className="h-5 w-5 text-teal-100" />
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline justify-between">
              <span className="text-4xl font-black">{dashboard.health_score}/100</span>
              <span className="text-xs bg-white/20 px-2 py-1 rounded-full font-medium flex items-center gap-1">
                <TrendingUp className="h-3 w-3" /> {dashboard.score_trend} this week
              </span>
            </div>
            <div className="mt-4 w-full bg-black/10 rounded-full h-2 overflow-hidden">
              <div className="bg-white h-full rounded-full transition-all duration-1000" style={{ width: `${dashboard.health_score}%` }}></div>
            </div>
            <p className="text-xs text-teal-100 mt-2">Status: <strong className="text-white">{healthStatus.text}</strong></p>
          </CardContent>
        </Card>

        {/* Daily Tip Card */}
        <Card className="shadow-md border-slate-200 dark:border-slate-800 md:col-span-2 flex flex-col justify-between bg-white dark:bg-slate-900">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-amber-500" /> Daily Health Tip
            </CardTitle>
            <span className="text-xs text-slate-400 font-medium">AI Generated</span>
          </CardHeader>
          <CardContent>
            <p className="text-slate-600 dark:text-slate-300 italic text-sm md:text-base">
              &ldquo;{dashboard.daily_tip}&rdquo;
            </p>
            <div className="mt-4 flex gap-3">
              <Link href="/chat">
                <Button size="sm" className="bg-teal-600 hover:bg-teal-700 text-white gap-2">
                  <Bot className="h-4 w-4" /> Ask AI Assistant
                </Button>
              </Link>
              <Link href="/reports">
                <Button size="sm" variant="outline" className="gap-2">
                  <Upload className="h-4 w-4" /> Upload Report
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* MAIN CONTENT GRID */}
      <div className="grid gap-6 lg:grid-cols-3">
        <motion.div variants={item} className="lg:col-span-2 space-y-6">
          
          {/* Health Trend Graph */}
          <Card className="shadow-md border-slate-200 dark:border-slate-800">
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-lg">Health Trend</CardTitle>
                <CardDescription>Your health score over the last 7 days</CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-[200px] w-full mt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={dashboard.health_trend_data || []}>
                    <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#888' }} />
                    <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                    <Line type="monotone" dataKey="score" stroke="#0d9488" strokeWidth={3} dot={{ r: 4, fill: '#0d9488', strokeWidth: 0 }} activeDot={{ r: 6 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Appointments & Reminders Grid */}
          <div className="grid sm:grid-cols-2 gap-6">
            
            {/* Appointments Block */}
            <Card className="shadow-md border-slate-200 dark:border-slate-800 flex flex-col">
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Calendar className="h-5 w-5 text-blue-500" /> Appointments
                </CardTitle>
                <Link href="/appointments" className="text-xs font-semibold text-teal-600 hover:underline flex items-center">
                  View all <ChevronRight className="h-3 w-3" />
                </Link>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col gap-3">
                {dashboard.upcoming_appointments?.length ? (
                  dashboard.upcoming_appointments.map((appt) => (
                    <div key={appt.id} className="flex items-center justify-between rounded-xl bg-slate-50 border border-slate-100 p-3 dark:bg-slate-800/50 dark:border-slate-800">
                      <div>
                        <p className="font-semibold text-sm">{appt.doctor?.name || "Dr. Consultation"}</p>
                        <p className="text-xs text-slate-500">{appt.doctor?.specialty || "General Specialist"}</p>
                      </div>
                      <p className="text-xs font-medium text-blue-600 bg-blue-50 dark:bg-blue-900/30 px-2 py-1 rounded-md">
                        {formatDate(appt.scheduled_at)}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="flex-1 flex flex-col items-center justify-center text-center p-6 border-2 border-dashed border-slate-100 dark:border-slate-800 rounded-xl bg-slate-50/50 dark:bg-slate-900/25">
                    <Calendar className="h-8 w-8 text-slate-300 mb-2" />
                    <p className="text-sm font-medium text-slate-600 dark:text-slate-400">No upcoming appointments</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Reminders Block */}
            <Card className="shadow-md border-slate-200 dark:border-slate-800 flex flex-col">
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Pill className="h-5 w-5 text-teal-500" /> Reminders
                </CardTitle>
                <Link href="/reminders" className="text-xs font-semibold text-teal-600 hover:underline flex items-center">
                  View all <ChevronRight className="h-3 w-3" />
                </Link>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col gap-3">
                {dashboard.medicine_reminders?.length ? (
                  dashboard.medicine_reminders.map((rem) => (
                    <div key={rem.id} className="flex items-center justify-between rounded-xl bg-slate-50 border border-slate-100 p-3 dark:bg-slate-800/50 dark:border-slate-800">
                      <div>
                        <p className="font-semibold text-sm">{rem.medicine_name}</p>
                        <p className="text-xs text-slate-500">{rem.dosage}</p>
                      </div>
                      <span className="text-xs font-medium text-teal-600 bg-teal-50 dark:bg-teal-900/30 px-2 py-1 rounded-md">
                        {rem.timing}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="flex-1 flex flex-col items-center justify-center text-center p-6 border-2 border-dashed border-slate-100 dark:border-slate-800 rounded-xl bg-slate-50/50 dark:bg-slate-900/25">
                    <Pill className="h-8 w-8 text-slate-300 mb-2" />
                    <p className="text-sm font-medium text-slate-600 dark:text-slate-400">No active medicine reminders</p>
                  </div>
                )}
              </CardContent>
            </Card>

          </div>
        </motion.div>

        {/* SIDEBAR COLUMN (Recent Reports & Doctors) */}
        <motion.div variants={item} className="space-y-6">
          
          {/* Recent Reports */}
          <Card className="shadow-md border-slate-200 dark:border-slate-800">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="flex items-center gap-2 text-lg">
                <FileText className="h-5 w-5 text-indigo-500" /> Recent Reports
              </CardTitle>
              <Link href="/reports" className="text-xs font-semibold text-teal-600 hover:underline">
                View all
              </Link>
            </CardHeader>
            <CardContent className="space-y-3">
              {dashboard.recent_reports?.length ? (
                dashboard.recent_reports.map((rep) => (
                  <div key={rep.id} className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950 text-indigo-600">
                        <FileText className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold truncate max-w-[150px]">{rep.title}</p>
                        <p className="text-xs text-slate-400">{formatDate(rep.created_at)}</p>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-500 text-center py-4">No reports uploaded yet.</p>
              )}
            </CardContent>
          </Card>

          {/* Recommended Doctors */}
          <Card className="shadow-md border-slate-200 dark:border-slate-800">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-lg">
                <Stethoscope className="h-5 w-5 text-teal-500" /> Top Specialists
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {dashboard.recommended_doctors?.length ? (
                dashboard.recommended_doctors.map((doc) => (
                  <div key={doc.id} className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                    <div>
                      <p className="text-sm font-semibold">{doc.name}</p>
                      <p className="text-xs text-slate-500">{doc.specialty}</p>
                    </div>
                    <Link href={`/appointments/book?doctorId=${doc.id}`}>
                      <Button size="sm" variant="outline" className="text-xs h-8">
                        Book
                      </Button>
                    </Link>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-500 text-center py-4">No recommendations available.</p>
              )}
            </CardContent>
          </Card>

        </motion.div>
      </div>
    </motion.div>
  );
}