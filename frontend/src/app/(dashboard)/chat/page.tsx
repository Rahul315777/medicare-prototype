"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { chatApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Bot, Loader2, Mic, Send, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";

interface Message {
  id: string;
  role: string;
  content: string;
  confidence?: number;
  sources?: { content: string }[];
}

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [language, setLanguage] = useState("en");
  const [messages, setMessages] = useState<Message[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatApi.createSession(language).then((r) => setSessionId(r.data.id));
  }, [language]);

  const sendMutation = useMutation({
    mutationFn: (content: string) => chatApi.sendMessage(sessionId!, content, language),
    onSuccess: (res) => {
      setMessages((prev) => [...prev, res.data]);
    },
  });

  const handleSend = () => {
    if (!input.trim() || !sessionId) return;
    const userMsg: Message = { id: Date.now().toString(), role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    sendMutation.mutate(input);
    setInput("");
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    // FIX 1: Explicit fixed height for entire page container so scroll stays inside
    <div className="flex h-[calc(100vh-5rem)] flex-col">
      <div className="mb-4 flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-bold">AI Health Assistant</h1>
          <p className="text-slate-500">Educational medical information powered by RAG</p>
        </div>
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="rounded-xl border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
        >
          <option value="en">English</option>
          <option value="hi">हिंदी (Hindi)</option>
        </select>
      </div>

      {/* FIX 2: min-h-0 and flex-1 keep the card from overflowing the viewport */}
      <Card className="flex flex-1 flex-col overflow-hidden min-h-0">
        <CardContent className="flex flex-1 flex-col p-0 overflow-hidden">
          
          {/* FIX 3: Added clean vertical scrolling (overflow-y-auto) & smooth scrolling properties */}
          <div className="flex-1 space-y-4 overflow-y-auto p-6 scroll-smooth">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <Bot className="mb-4 h-12 w-12 text-teal-500" />
                <p className="text-lg font-medium">How can I help you today?</p>
                <p className="text-sm text-slate-500">Ask about symptoms, medicines, or general health</p>
              </div>
            )}
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn("flex gap-3", msg.role === "user" ? "justify-end" : "justify-start")}
              >
                {msg.role === "assistant" && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-teal-100 dark:bg-teal-900">
                    <Bot className="h-4 w-4 text-teal-600" />
                  </div>
                )}
                <div
                  className={cn(
                    "max-w-[75%] rounded-2xl px-4 py-3 text-sm",
                    msg.role === "user"
                      ? "bg-teal-600 text-white"
                      : "bg-slate-100 dark:bg-slate-800"
                  )}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  {msg.confidence && (
                    <p className="mt-2 text-xs opacity-70">Confidence: {msg.confidence.toFixed(0)}%</p>
                  )}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 border-t border-slate-200/30 pt-2 dark:border-slate-600">
                      <p className="text-xs font-medium opacity-70">Sources:</p>
                      {msg.sources.slice(0, 2).map((s, i) => (
                        <p key={i} className="text-xs opacity-60 truncate">{s.content}</p>
                      ))}
                    </div>
                  )}
                </div>
                {msg.role === "user" && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-200 dark:bg-slate-700">
                    <User className="h-4 w-4" />
                  </div>
                )}
              </motion.div>
            ))}
            {sendMutation.isPending && (
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin" /> AI is thinking...
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input Area stays pinned at the bottom */}
          <div className="border-t border-slate-200 p-4 dark:border-slate-800 shrink-0">
            <div className="flex gap-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                placeholder={language === "hi" ? "अपना प्रश्न पूछें..." : "Ask a health question..."}
                className="flex-1"
              />
              <Button variant="outline" size="icon" title="Voice input">
                <Mic className="h-4 w-4" />
              </Button>
              <Button onClick={handleSend} disabled={sendMutation.isPending || !input.trim()}>
                <Send className="h-4 w-4" />
              </Button>
            </div>
            <p className="mt-2 text-center text-xs text-slate-400">
              Not medical advice. Consult a doctor for diagnosis and treatment.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}