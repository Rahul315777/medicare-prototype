"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Heart, Loader2, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/input";

import { authApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

// Framer Motion Variants
const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 15 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } },
};

export default function RegisterPage() {
  const [form, setForm] = useState({ 
    email: "", 
    password: "", 
    confirmPassword: "", 
    full_name: "", 
    phone: "",
    termsAccepted: false 
  });
  
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  const { isAuthenticated } = useAuthStore();
  const router = useRouter();

  // Redirect if already logged in
  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, router]);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // --- FRONTEND VALIDATIONS ---
    if (!/^[A-Za-z\s]+$/.test(form.full_name)) {
      return setError("Name can only contain letters and spaces.");
    }
    if (form.phone && !/^(\+91[\-\s]?)?[0-9]{10}$/.test(form.phone)) {
      return setError("Invalid phone number. Must be 10 digits (e.g. 9876543210 or +919876543210).");
    }
    const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$/;
    if (!passwordRegex.test(form.password)) {
      return setError("Password must be 8+ chars, 1 uppercase, 1 lowercase, 1 number, and 1 special character.");
    }
    if (form.password !== form.confirmPassword) {
      return setError("Passwords do not match.");
    }
    if (!form.termsAccepted) {
      return setError("You must agree to the Terms and Privacy Policy.");
    }

    setLoading(true);

    try {
      const { confirmPassword, termsAccepted, ...apiPayload } = form;
      
      await authApi.register(apiPayload);
      
      toast.success("Registration successful! Please log in.");
      router.push("/login");
      
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Registration failed. Please try again.";
      setError(msg);
      toast.error("Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 via-teal-50/40 to-emerald-50/30 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 p-4 py-10">
      <motion.div variants={containerVariants} initial="hidden" animate="show" className="w-full max-w-md">
        
        <motion.div variants={itemVariants} className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-500 to-emerald-600 shadow-xl shadow-teal-500/30">
            <Heart className="h-7 w-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Create Account</h1>
          <p className="text-slate-500 dark:text-slate-400">Join MediCare AI for smarter healthcare</p>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className="border-slate-200/60 dark:border-slate-800 shadow-xl shadow-slate-200/40 dark:shadow-none backdrop-blur-xl bg-white/90 dark:bg-slate-900/90">
            <CardHeader>
              <CardTitle>Register</CardTitle>
              <CardDescription>Fill in your details to get started</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleRegister} className="space-y-4">
                
                {error && (
                  <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="rounded-lg bg-red-50 p-3 text-sm text-red-600 dark:bg-red-950/50 dark:text-red-400 border border-red-100 dark:border-red-900/50">
                    {error}
                  </motion.div>
                )}

                <div className="space-y-2">
                  <Label>Full Name</Label>
                  <Input 
                    value={form.full_name} 
                    onChange={(e) => setForm({ ...form, full_name: e.target.value })} 
                    autoComplete="name" 
                    disabled={loading} 
                    required 
                    className="bg-white dark:bg-slate-950"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input 
                    type="email" 
                    value={form.email} 
                    onChange={(e) => setForm({ ...form, email: e.target.value })} 
                    autoComplete="email" 
                    disabled={loading}
                    required 
                    className="bg-white dark:bg-slate-950"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Phone (Optional)</Label>
                  <Input 
                    value={form.phone} 
                    onChange={(e) => setForm({ ...form, phone: e.target.value })} 
                    placeholder="+91..." 
                    autoComplete="tel" 
                    disabled={loading}
                    className="bg-white dark:bg-slate-950"
                  />
                </div>

                {/* Password Fields */}
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Password</Label>
                    <div className="relative">
                      <Input 
                        type={showPassword ? "text" : "password"} 
                        value={form.password} 
                        onChange={(e) => setForm({ ...form, password: e.target.value })} 
                        autoComplete="new-password" 
                        disabled={loading}
                        className="pr-10 bg-white dark:bg-slate-950"
                        required 
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-700 dark:text-slate-400 transition-colors"
                        disabled={loading}
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Confirm</Label>
                    <div className="relative">
                      <Input 
                        type={showConfirmPassword ? "text" : "password"} 
                        value={form.confirmPassword} 
                        onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })} 
                        autoComplete="new-password" 
                        disabled={loading}
                        className="pr-10 bg-white dark:bg-slate-950"
                        required 
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-700 dark:text-slate-400 transition-colors"
                        disabled={loading}
                      >
                        {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Terms Checkbox - Fixed using native input */}
                <div className="flex items-start space-x-2 py-2">
                  <input 
                    type="checkbox"
                    id="terms" 
                    checked={form.termsAccepted}
                    onChange={(e) => setForm({...form, termsAccepted: e.target.checked})}
                    disabled={loading}
                    className="mt-1 h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-600 dark:border-slate-700 dark:bg-slate-950"
                  />
                  <div className="grid gap-1.5 leading-none">
                    <Label htmlFor="terms" className="text-sm font-medium leading-none cursor-pointer">
                      I agree to the Terms and Privacy Policy
                    </Label>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Your data is secure and encrypted.
                    </p>
                  </div>
                </div>

                <Button type="submit" className="w-full bg-teal-600 hover:bg-teal-700 text-white" disabled={loading}>
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Creating Account...
                    </>
                  ) : (
                    "Create Account"
                  )}
                </Button>
              </form>

              {/* Google Register */}
              <div className="mt-6">
                <div className="relative mb-6">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-slate-200 dark:border-slate-800" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-white dark:bg-slate-900 px-2 text-slate-500">Or sign up with</span>
                  </div>
                </div>

                <Button variant="outline" type="button" disabled={loading} className="w-full bg-white dark:bg-slate-950 border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900">
                  <svg className="mr-2 h-4 w-4" aria-hidden="true" focusable="false" data-prefix="fab" data-icon="google" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 488 512">
                    <path fill="currentColor" d="M488 261.8C488 403.3 391.1 504 248 504 110.8 504 0 393.2 0 256S110.8 8 248 8c66.8 0 123 24.5 166.3 64.9l-67.5 64.9C258.5 52.6 94.3 116.6 94.3 256c0 86.5 69.1 156.6 153.7 156.6 98.2 0 135-70.4 140.8-106.9H248v-85.3h236.1c2.3 12.7 3.9 24.9 3.9 41.4z"></path>
                  </svg>
                  Google
                </Button>
              </div>

              <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
                Already have an account?{" "}
                <Link href="/login" className="font-semibold text-teal-600 dark:text-teal-400 hover:underline transition-colors">
                  Sign In
                </Link>
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>
    </div>
  );
}