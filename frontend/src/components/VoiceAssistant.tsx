"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Mic, Square, Loader2, Bot, User, MessageSquareText, X, AlertTriangle } from "lucide-react";
import { chatApi } from "@/lib/api";

type LanguageCode = "auto" | "en" | "hi" | "hinglish";

const LANGUAGES: { code: LanguageCode; label: string }[] = [
  { code: "auto", label: "Auto Detect" },
  { code: "en", label: "English" },
  { code: "hi", label: "Hindi" },
  { code: "hinglish", label: "Hinglish" },
];

interface Turn {
  id: string;
  transcript: string;
  reply: string;
  isError: boolean;
  hasAudio: boolean;
}

export default function VoiceAssistant() {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [language, setLanguage] = useState<LanguageCode>("auto");
  const [micError, setMicError] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [panelOpen, setPanelOpen] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);
  const router = useRouter();

  const startRecording = async () => {
    setMicError(null);

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (error) {
      // Graceful fallback #1: mic permission denied / no mic available
      console.error("Microphone access denied:", error);
      setMicError("Microphone access was denied or unavailable. You can continue by typing in the chat instead.");
      setPanelOpen(true);
      return;
    }

    try {
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => handleRecordingStop();

      mediaRecorder.start();
      setIsRecording(true);
      setPanelOpen(true);
    } catch (error) {
      // Graceful fallback #2: MediaRecorder unsupported/failed to start
      console.error("Could not start recording:", error);
      setMicError("Voice recording isn't available on this device/browser right now. Please use the text chat instead.");
      setPanelOpen(true);
      stream.getTracks().forEach((track) => track.stop());
    }
  };

  const handleRecordingStop = async () => {
    setIsProcessing(true);
    const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });

    if (audioBlob.size === 0) {
      // Graceful fallback #3: empty recording (e.g. stopped instantly)
      pushTurn({ transcript: "", reply: "I didn't catch any audio. Please try again, or type your question instead.", isError: true, hasAudio: false });
      setIsProcessing(false);
      return;
    }

    const audioFile = new File([audioBlob], "voice.webm", { type: "audio/webm" });

    try {
      const res = await chatApi.voiceChat(audioFile, language);
      const data = res.data;

      // Backend STT failure (empty transcript) surfaces as action: "error"
      if (data.action === "error" || !data.transcript) {
        pushTurn({
          transcript: data.transcript || "",
          reply: data.answer || "Sorry, I couldn't understand that. Please try again or type instead.",
          isError: true,
          hasAudio: false,
        });
        return;
      }

      // Show the transcript + reply for user verification, regardless of
      // whether audio playback works.
      pushTurn({
        transcript: data.transcript,
        reply: data.answer || "",
        isError: false,
        hasAudio: Boolean(data.audio_base64),
      });

      // Play audio if TTS succeeded; if not, the text reply above is
      // already visible — graceful fallback to text-only.
      if (data.audio_base64) {
        try {
          const audio = new Audio("data:audio/mp3;base64," + data.audio_base64);
          await audio.play();
        } catch (playError) {
          console.warn("Audio playback failed, text reply still shown:", playError);
        }
      }

      if (data.action === "navigate" && data.target) {
        router.push(data.target);
      } else if (data.action === "book" && data.target) {
        router.push(`${data.target}?doctor=${data.command_data?.doctor_name || ""}`);
      }
    } catch (error) {
      // Graceful fallback #4: API/network/timeout failure
      console.error("Voice processing failed:", error);
      pushTurn({
        transcript: "",
        reply: "Sorry, I couldn't process that voice message (connection issue). Please try again or use text chat.",
        isError: true,
        hasAudio: false,
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const pushTurn = (turn: Omit<Turn, "id">) => {
    setTurns((prev) => [...prev.slice(-4), { ...turn, id: crypto.randomUUID() }]);
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
      {/* Transcript / conversation verification panel */}
      {panelOpen && (
        <div className="w-80 max-w-[90vw] rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-2xl overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
            <span className="text-xs font-semibold text-slate-600 dark:text-slate-300 flex items-center gap-1.5">
              <MessageSquareText className="h-3.5 w-3.5" /> Voice Assistant
            </span>
            <button onClick={() => setPanelOpen(false)} className="text-slate-400 hover:text-slate-600">
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Language selector */}
          <div className="flex flex-wrap gap-1.5 px-4 py-2.5 border-b border-slate-100 dark:border-slate-800">
            {LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                onClick={() => setLanguage(lang.code)}
                className={`px-2.5 py-1 rounded-full text-xs font-medium transition ${
                  language === lang.code
                    ? "bg-teal-600 text-white"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                }`}
              >
                {lang.label}
              </button>
            ))}
          </div>

          {/* Mic permission / hard error banner */}
          {micError && (
            <div className="mx-4 mt-3 flex items-start gap-2 rounded-lg bg-amber-50 dark:bg-amber-950/30 p-2.5 text-xs text-amber-800 dark:text-amber-400">
              <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              <span>{micError}</span>
            </div>
          )}

          {/* Conversation / transcript history */}
          <div className="max-h-72 overflow-y-auto px-4 py-3 space-y-3">
            {turns.length === 0 && !micError && (
              <p className="text-xs text-slate-400 text-center py-4">
                Tap the mic and speak — your words will show up here so you can confirm what was understood.
              </p>
            )}
            {turns.map((turn) => (
              <div key={turn.id} className="space-y-1.5">
                {turn.transcript && (
                  <div className="flex items-start gap-2 justify-end">
                    <p className="text-xs bg-teal-600 text-white rounded-2xl rounded-tr-sm px-3 py-1.5 max-w-[85%]">
                      {turn.transcript}
                    </p>
                    <User className="h-4 w-4 text-slate-400 mt-1 shrink-0" />
                  </div>
                )}
                <div className="flex items-start gap-2">
                  <Bot className={`h-4 w-4 mt-1 shrink-0 ${turn.isError ? "text-amber-500" : "text-teal-600"}`} />
                  <p
                    className={`text-xs rounded-2xl rounded-tl-sm px-3 py-1.5 max-w-[85%] ${
                      turn.isError
                        ? "bg-amber-50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-400"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200"
                    }`}
                  >
                    {turn.reply}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Always-available text fallback */}
          <button
            onClick={() => router.push("/chat")}
            className="w-full flex items-center justify-center gap-1.5 px-4 py-2.5 border-t border-slate-100 dark:border-slate-800 text-xs font-medium text-teal-600 hover:bg-teal-50 dark:hover:bg-teal-950/30 transition"
          >
            <MessageSquareText className="h-3.5 w-3.5" /> Continue in text chat instead
          </button>
        </div>
      )}

      {/* Status bubble */}
      {isRecording && (
        <div className="animate-bounce rounded-full bg-slate-800 px-4 py-2 text-xs font-medium text-white shadow-lg">
          Listening... Click to stop.
        </div>
      )}
      {isProcessing && (
        <div className="animate-pulse rounded-full bg-teal-600 px-4 py-2 text-xs font-medium text-white shadow-lg">
          Thinking...
        </div>
      )}

      {/* Floating Action Button */}
      <button
        onClick={isRecording ? stopRecording : startRecording}
        disabled={isProcessing}
        className={`flex h-14 w-14 items-center justify-center rounded-full shadow-2xl transition-all duration-300 hover:scale-110 active:scale-95 ${
          isRecording
            ? "bg-red-500 hover:bg-red-600"
            : isProcessing
              ? "bg-teal-500 cursor-not-allowed"
              : "bg-teal-600 hover:bg-teal-700"
        }`}
      >
        {isProcessing ? (
          <Loader2 className="h-6 w-6 animate-spin text-white" />
        ) : isRecording ? (
          <Square className="h-5 w-5 fill-current text-white" />
        ) : (
          <Mic className="h-6 w-6 text-white" />
        )}
      </button>
    </div>
  );
}