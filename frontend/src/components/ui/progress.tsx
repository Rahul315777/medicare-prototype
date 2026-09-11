"use client";

import { cn } from "@/lib/utils";
import * as Progress from "@radix-ui/react-progress";

export function ProgressBar({ value, className }: { value: number; className?: string }) {
  return (
    <Progress.Root
      className={cn("relative h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700", className)}
      value={value}
    >
      <Progress.Indicator
        className="h-full rounded-full bg-gradient-to-r from-teal-500 to-emerald-500 transition-all duration-500"
        style={{ width: `${value}%` }}
      />
    </Progress.Root>
  );
}
