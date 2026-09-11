"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { authApi } from "@/lib/api";
import Link from "next/link";
import { useState } from "react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await authApi.forgotPassword(email);
    setSent(true);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 via-teal-50/40 to-emerald-50/30">
      <Card className="w-full max-w-md">
        <CardHeader><CardTitle>Forgot Password</CardTitle></CardHeader>
        <CardContent>
          {sent ? (
            <p className="text-sm text-teal-600">If the email exists, a reset OTP has been sent.</p>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2"><Label>Email</Label><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></div>
              <Button type="submit" className="w-full">Send Reset OTP</Button>
            </form>
          )}
          <Link href="/login" className="mt-4 block text-center text-sm text-teal-600 hover:underline">Back to Login</Link>
        </CardContent>
      </Card>
    </div>
  );
}
