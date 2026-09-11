"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Mic, Square, Loader2, Bot } from "lucide-react";
import { chatApi } from "@/lib/api";

export default function VoiceAssistant() {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);
  const router = useRouter();

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        setIsProcessing(true);
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const audioFile = new File([audioBlob], "voice.webm", { type: "audio/webm" });

        try {
          // Backend API ko aawaz bhej rahe hain
          const res = await chatApi.voiceChat(audioFile, "en");
          const data = res.data;

          // 1. Aawaz Play Karein (Text-to-Speech)
          if (data.audio_base64) {
            const audio = new Audio("data:audio/mp3;base64," + data.audio_base64);
            audio.play();
          }

          // 2. App Navigate Karein (Agar user ne bola "open reports")
          if (data.action === "navigate" && data.target) {
            router.push(data.target);
          } 
          // 3. Book Appointment Navigate
          else if (data.action === "book" && data.target) {
            router.push(`${data.target}?doctor=${data.command_data?.doctor_name || ""}`);
          }
        } catch (error) {
          console.error("Voice processing failed:", error);
          alert("Sorry, I couldn't process your voice right now.");
        } finally {
          setIsProcessing(false);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error("Microphone access denied:", error);
      alert("Please allow microphone access to use the voice assistant.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      // Stop all mic tracks to free up the browser indicator
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
      {/* Recording Indicator Bubble */}
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