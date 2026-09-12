"use client";

import { useAuthStore } from "@/store/auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import Link from "next/link";
import { LayoutDashboard, MessageSquare, FileText, Calendar, LogOut, Stethoscope } from "lucide-react";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { token, user, logout } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (!token) router.push("/login");
  }, [token, router]);

  if (!token) return null;

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-950">
      <aside className="w-64 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hidden md:flex flex-col p-6">
        <div className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-teal-500 mb-8">
          MediCare<span className="text-blue-600">AI</span>
        </div>
        <nav className="space-y-2 flex-1">
          <Link href="/dashboard" className="flex items-center gap-3 px-4 py-3 rounded-xl bg-teal-50 dark:bg-teal-950/50 text-teal-600 dark:text-teal-400 font-semibold text-sm">
            <LayoutDashboard size={18} /> Dashboard
          </Link>
          <Link href="/chat" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 font-medium text-sm transition">
            <MessageSquare size={18} /> AI Chat
          </Link>
          <Link href="/reports" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 font-medium text-sm transition">
            <FileText size={18} /> Reports
          </Link>
          <Link href="/doctors" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 font-medium text-sm transition">
            <Calendar size={18} /> Appointments
          </Link>
          {user?.role === "doctor" && (
            <Link href="/doctor/appointments" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 font-medium text-sm transition">
              <Stethoscope size={18} /> Doctor Portal
            </Link>
          )}
        </nav>
        <button 
          onClick={() => { logout(); router.push("/login"); }}
          className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-red-50 text-red-600 font-medium text-sm transition mt-auto"
        >
          <LogOut size={18} /> Logout
        </button>
      </aside>

      <main className="flex-1 overflow-y-auto p-6 lg:p-10">
        {children}
      </main>
    </div>
  );
}