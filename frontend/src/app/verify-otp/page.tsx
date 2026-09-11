"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { authApi } from "@/lib/api";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

export default function VerifyOtpPage() {
  const searchParams = useSearchParams();
  const email = searchParams.get("email") || "";
  const [otp, setOtp] = useState("");
  const [message, setMessage] = useState("");

  const handleVerify = async () => {
    try {
      await authApi.verifyOtp({ email, otp });
      setMessage("Verified! You can now sign in.");
    } catch {
      setMessage("Invalid OTP. Please try again.");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 via-teal-50/40 to-emerald-50/30">
      <Card className="w-full max-w-md">
        <CardHeader><CardTitle>Verify Email</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-slate-500">Enter the 6-digit OTP sent to {email}</p>
          <div className="space-y-2"><Label>OTP</Label><Input value={otp} onChange={(e) => setOtp(e.target.value)} maxLength={6} placeholder="000000" /></div>
          {message && <p className="text-sm text-teal-600">{message}</p>}
          <Button onClick={handleVerify} className="w-full">Verify</Button>
          <Link href="/login" className="block text-center text-sm text-teal-600 hover:underline">Back to Login</Link>
        </CardContent>
      </Card>
    </div>
  );
}
