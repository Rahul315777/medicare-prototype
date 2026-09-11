"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Star, MessageSquare, FileText, Calendar, Shield, Activity, Phone } from "lucide-react";

import { useAuthStore } from "@/store/auth";

// --- Data Arrays ---
const STATS = [
  { label: "Patients Helped", value: "5000+" },
  { label: "Verified Doctors", value: "150+" },
  { label: "AI Accuracy", value: "98%" },
  { label: "Support", value: "24x7" },
];

// YAHAN BADLAV KIYA GAYA HAI: Har feature mein 'href' joda gaya hai
const FEATURES = [
  { title: "AI Chat", href: "/chat", desc: "Instant medical guidance and symptom checking using advanced AI.", icon: <MessageSquare className="h-8 w-8 text-blue-600 dark:text-blue-400" /> },
  { title: "Medical Reports", href: "/reports", desc: "Upload reports (OCR) for instant simplified explanations.", icon: <FileText className="h-8 w-8 text-teal-600 dark:text-teal-400" /> },
  { title: "Medicine Reminder", href: "/prescriptions", desc: "Never miss a dose with automated WhatsApp/SMS alerts.", icon: <Activity className="h-8 w-8 text-blue-600 dark:text-blue-400" /> },
  { title: "Emergency SOS", href: "/emergency", desc: "One-tap emergency alerts to nearest hospitals & contacts.", icon: <Phone className="h-8 w-8 text-red-500" /> },
  { title: "Telemedicine", href: "/doctors", desc: "Connect via video/audio with verified specialist doctors.", icon: <Calendar className="h-8 w-8 text-teal-600 dark:text-teal-400" /> },
  { title: "Secure Data", href: "/dashboard", desc: "End-to-end encrypted medical data & HIPAA compliant.", icon: <Shield className="h-8 w-8 text-blue-600 dark:text-blue-400" /> },
];

const TESTIMONIALS = [
  { name: "Rahul Sharma", text: "MediCare AI made managing my health so easy. The daily reminders are a lifesaver.", role: "Patient" },
  { name: "Priya Singh", text: "The AI Report Analysis saved me hours of Googling. It broke down my blood test perfectly.", role: "Software Engineer" },
  { name: "Aman Verma", text: "Booking a consultation is super fast. Zero waiting time and excellent doctors.", role: "Business Owner" },
];

const FAQS = [
  { q: "How secure is my medical data?", a: "We use bank-grade AES-256 encryption. Your data is strictly confidential, HIPAA compliant, and never shared with third parties." },
  { q: "Can the AI replace a real doctor?", a: "No. MediCare AI is designed to assist and provide preliminary guidance. Always consult our verified doctors for proper diagnosis and treatment." },
  { q: "Is MediCare AI completely free?", a: "We offer a generous free tier for basic AI chats and reminders. Premium features like direct Telemedicine require a subscription." },
  { q: "Can I upload handwritten medical reports?", a: "Yes! Our advanced OCR technology can read and analyze both printed and handwritten medical documents." },
];

// --- Animation Variants ---
const fadeUp = { hidden: { opacity: 0, y: 30 }, show: { opacity: 1, y: 0, transition: { duration: 0.5 } } };
const staggerContainer = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.1 } } };

export default function Home() {
  const [openFaq, setOpenFaq] = useState<string | null>(null);
  const router = useRouter();
  
  const { isAuthenticated, _hasHydrated } = useAuthStore();

  useEffect(() => {
    if (_hasHydrated && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [_hasHydrated, isAuthenticated, router]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 font-sans text-slate-900 dark:text-slate-50 selection:bg-blue-600 selection:text-white transition-colors duration-300 overflow-hidden">
      
      {/* ================= NAVBAR ================= */}
      <nav className="fixed top-0 w-full z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-teal-500">
            MediCare<span className="text-blue-600 dark:text-blue-500">AI</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600 dark:text-slate-300">
            <Link href="/" className="hover:text-blue-600 transition">Home</Link>
            <Link href="#features" className="hover:text-blue-600 transition">Features</Link>
            <Link href="#testimonials" className="hover:text-blue-600 transition">Reviews</Link>
            <Link href="#faq" className="hover:text-blue-600 transition">FAQ</Link>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login" className="hidden sm:block text-sm font-semibold text-slate-700 dark:text-slate-200 hover:text-blue-600 transition">
              Login
            </Link>
            <Link href="/register" className="px-5 py-2 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-full shadow-lg hover:shadow-blue-600/30 transition-all transform hover:-translate-y-0.5">
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* ================= HERO SECTION ================= */}
      <section className="relative pt-32 pb-20 lg:pt-48 lg:pb-32">
        <motion.div 
          animate={{ y: [0, -30, 0], x: [0, 20, 0], scale: [1, 1.1, 1] }} 
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
          className="absolute top-0 right-0 -mr-20 -mt-20 w-96 h-96 rounded-full bg-blue-400/20 dark:bg-blue-600/20 blur-3xl pointer-events-none" 
        />
        <motion.div 
          animate={{ y: [0, 40, 0], x: [0, -30, 0], scale: [1, 1.2, 1] }} 
          transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
          className="absolute bottom-0 left-0 -ml-20 w-72 h-72 rounded-full bg-teal-400/20 dark:bg-teal-600/20 blur-3xl pointer-events-none" 
        />

        <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-12 items-center relative z-10">
          <motion.div variants={staggerContainer} initial="hidden" animate="show" className="text-center lg:text-left">
            <motion.div variants={fadeUp} className="inline-block px-4 py-1.5 mb-6 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-sm font-bold tracking-wide uppercase">
              Your Intelligent Healthcare Companion
            </motion.div>
            <motion.h1 variants={fadeUp} className="text-5xl lg:text-7xl font-extrabold leading-tight mb-6">
              Next-Gen <br className="hidden lg:block"/>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-teal-500">
                Medical Care
              </span>
            </motion.h1>
            <motion.p variants={fadeUp} className="text-lg text-slate-600 dark:text-slate-400 mb-8 max-w-2xl mx-auto lg:mx-0">
              Experience the future of healthcare. Upload reports, chat with our AI, book specialist doctors, and manage your health dashboard seamlessly.
            </motion.p>
            <motion.div variants={fadeUp} className="flex flex-col sm:flex-row items-center gap-4 justify-center lg:justify-start">
              <Link href="/register" className="w-full sm:w-auto px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-full font-bold shadow-xl hover:shadow-blue-600/40 transition-all transform hover:-translate-y-1">
                Create Free Account
              </Link>
              <Link href="/login" className="w-full sm:w-auto px-8 py-4 bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 hover:border-blue-600 dark:hover:border-blue-500 text-slate-700 dark:text-slate-200 rounded-full font-bold transition-all hover:bg-slate-50 dark:hover:bg-slate-800/50">
                Talk to AI 🤖
              </Link>
            </motion.div>
          </motion.div>
          
          <motion.div 
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="hidden lg:flex justify-center relative"
          >
            <div className="relative w-full max-w-md aspect-square">
              <motion.div 
                animate={{ y: [-10, 10, -10] }} 
                transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
                className="absolute inset-0 bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col"
              >
                <div className="h-12 border-b border-slate-100 dark:border-slate-800 flex items-center px-4 gap-2 bg-slate-50 dark:bg-slate-950">
                  <div className="w-3 h-3 rounded-full bg-red-400"></div>
                  <div className="w-3 h-3 rounded-full bg-amber-400"></div>
                  <div className="w-3 h-3 rounded-full bg-green-400"></div>
                </div>
                <div className="p-6 flex-1 bg-slate-50/50 dark:bg-slate-900/50 flex flex-col gap-4">
                  <div className="flex justify-between items-center mb-2">
                    <div className="h-6 w-32 bg-slate-200 dark:bg-slate-800 rounded-md"></div>
                    <div className="h-8 w-8 bg-blue-100 dark:bg-blue-900/50 rounded-full"></div>
                  </div>
                  <div className="self-end bg-blue-600 text-white p-3 rounded-2xl rounded-tr-sm w-3/4 text-sm">
                    Can you analyze my recent blood report?
                  </div>
                  <div className="self-start bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700 p-3 rounded-2xl rounded-tl-sm w-5/6 text-sm shadow-sm">
                    Absolutely! Your hemoglobin is slightly low at 11.2 g/dL. I recommend adding iron-rich foods to your diet.
                  </div>
                </div>
              </motion.div>
              <motion.div 
                animate={{ y: [10, -10, 10] }} 
                transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: 1 }}
                className="absolute -right-8 top-1/4 bg-white dark:bg-slate-800 p-4 rounded-2xl shadow-xl border border-slate-100 dark:border-slate-700 flex items-center gap-4"
              >
                <div className="bg-green-100 dark:bg-green-900/30 p-2 rounded-full text-green-600">
                  <Activity size={24} />
                </div>
                <div>
                  <p className="text-xs text-slate-500 font-medium">Health Score</p>
                  <p className="text-xl font-bold">92/100</p>
                </div>
              </motion.div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ================= STATS SECTION ================= */}
      <section className="bg-blue-600 dark:bg-blue-700 py-12 relative z-20">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8 divide-x divide-blue-500/50 text-center">
          {STATS.map((stat) => (
            <div key={stat.label} className="flex flex-col">
              <span className="text-4xl md:text-5xl font-black text-white mb-2">{stat.value}</span>
              <span className="text-blue-100 font-medium">{stat.label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ================= FEATURES SECTION ================= */}
      <section id="features" className="py-24 px-6 max-w-7xl mx-auto">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Powerful Healthcare Features</h2>
          <p className="text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">
            Everything you need to monitor, manage, and improve your health in one super app.
          </p>
        </motion.div>
        
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {FEATURES.map((feat, index) => (
            <motion.div 
              key={feat.title} 
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
            >
              {/* YAHAN BADLAV KIYA GAYA HAI: Design ko Link ke andar daal diya hai */}
              <Link 
                href={feat.href}
                className="block h-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-8 rounded-3xl shadow-sm hover:shadow-xl hover:-translate-y-1 hover:border-blue-500 transition-all duration-300 group cursor-pointer"
              >
                <div className="mb-6 bg-blue-50 dark:bg-slate-800 w-16 h-16 flex items-center justify-center rounded-2xl group-hover:bg-blue-100 dark:group-hover:bg-blue-900/50 transition-colors">
                  {feat.icon}
                </div>
                <h3 className="text-xl font-bold mb-3 text-slate-800 dark:text-slate-100">{feat.title}</h3>
                <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
                  {feat.desc}
                </p>
              </Link>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ================= TESTIMONIALS ================= */}
      <section id="testimonials" className="py-24 bg-slate-100 dark:bg-slate-900/50 border-y border-slate-200 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Loved by Thousands</h2>
            <p className="text-slate-600 dark:text-slate-400">See what our users are saying about MediCare AI.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {TESTIMONIALS.map((t, index) => (
              <motion.div 
                key={t.name}
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="bg-white dark:bg-slate-950 p-8 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800"
              >
                <div className="flex gap-1 mb-4 text-amber-400">
                  {[...Array(5)].map((_, i) => <Star key={`star-${i}`} size={18} fill="currentColor" />)}
                </div>
                <p className="text-slate-700 dark:text-slate-300 mb-6 font-medium italic">&quot;{t.text}&quot;</p>
                <div>
                  <p className="font-bold text-slate-900 dark:text-white">{t.name}</p>
                  <p className="text-sm text-slate-500">{t.role}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ================= FAQ SECTION ================= */}
      <section id="faq" className="py-24 px-6 max-w-3xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Frequently Asked Questions</h2>
        </div>
        <div className="space-y-4">
          {FAQS.map((faq) => (
            <div key={faq.q} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden">
              <button 
                onClick={() => setOpenFaq(openFaq === faq.q ? null : faq.q)}
                className="w-full px-6 py-4 flex items-center justify-between font-bold text-left focus:outline-none"
              >
                {faq.q}
                <ChevronDown className={`transform transition-transform duration-300 ${openFaq === faq.q ? "rotate-180" : ""}`} />
              </button>
              <AnimatePresence>
                {openFaq === faq.q && (
                  <motion.div 
                    key="faq-answer"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="px-6 pb-4 text-slate-600 dark:text-slate-400"
                  >
                    {faq.a}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>
      </section>

      {/* ================= CTA BANNER ================= */}
      <section className="py-24 px-6 max-w-5xl mx-auto">
        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="bg-gradient-to-br from-blue-600 to-teal-500 rounded-[3rem] p-12 md:p-16 text-center text-white shadow-2xl relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 -mr-10 -mt-10 w-64 h-64 bg-white/10 rounded-full blur-2xl"></div>
          <h2 className="text-3xl md:text-5xl font-bold mb-6 relative z-10">Ready to Improve Your Health?</h2>
          <p className="text-blue-50 md:text-lg mb-10 max-w-2xl mx-auto relative z-10">
            Join thousands of users who are already taking control of their medical journey with MediCare AI.
          </p>
          <Link href="/register" className="inline-block px-10 py-4 bg-white text-blue-600 hover:bg-slate-50 rounded-full font-bold shadow-lg transform hover:-translate-y-1 transition-all relative z-10">
            Create Free Account
          </Link>
        </motion.div>
      </section>

      {/* ================= FOOTER ================= */}
      <footer className="bg-white dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800 pt-16 pb-8">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
          <div className="col-span-2 md:col-span-1">
            <div className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-teal-500 mb-4">
              MediCare AI
            </div>
            <p className="text-slate-500 dark:text-slate-400 text-sm">
              Your intelligent healthcare companion. Revolutionizing medical care with AI.
            </p>
          </div>
          <div>
            <h4 className="font-bold mb-4">Product</h4>
            <ul className="space-y-2 text-sm text-slate-500 dark:text-slate-400">
              <li><Link href="#features" className="hover:text-blue-600 transition">Features</Link></li>
              <li><Link href="/login" className="hover:text-blue-600 transition">AI Chat</Link></li>
              <li><Link href="/login" className="hover:text-blue-600 transition">Telemedicine</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold mb-4">Legal</h4>
            <ul className="space-y-2 text-sm text-slate-500 dark:text-slate-400">
              <li><Link href="/" className="hover:text-blue-600 transition">Privacy Policy</Link></li>
              <li><Link href="/" className="hover:text-blue-600 transition">Terms of Service</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold mb-4">Connect</h4>
            <ul className="space-y-2 text-sm text-slate-500 dark:text-slate-400">
              <li><Link href="/" className="hover:text-blue-600 transition">Contact Us</Link></li>
              <li>
                <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="hover:text-blue-600 transition">
                  Github Repository
                </a>
              </li>
            </ul>
          </div>
        </div>
        <div className="text-center text-sm text-slate-500 dark:text-slate-500 pt-8 border-t border-slate-100 dark:border-slate-900">
          © {new Date().getFullYear()} MediCare AI. All rights reserved.
        </div>
      </footer>
    </div>
  );
}