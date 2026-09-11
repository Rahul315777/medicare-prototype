import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date) {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(date));
}

export function getRiskColor(level: string) {
  switch (level?.toLowerCase()) {
    case "high":
      return "text-red-500 bg-red-500/10";
    case "moderate":
      return "text-amber-500 bg-amber-500/10";
    default:
      return "text-emerald-500 bg-emerald-500/10";
  }
}
