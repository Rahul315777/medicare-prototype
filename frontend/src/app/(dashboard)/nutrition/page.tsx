"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { medicalApi } from "@/lib/api";
import { useMutation } from "@tanstack/react-query";
import { Loader2, Upload, Utensils } from "lucide-react";
import { useRef } from "react";

export default function NutritionPage() {
  const fileRef = useRef<HTMLInputElement>(null);

  const analyzeMutation = useMutation({
    mutationFn: (file: File) => medicalApi.analyzeNutrition(file),
  });

  const data = analyzeMutation.data?.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">AI Nutrition Analyzer</h1>
        <p className="text-slate-500">Upload food photos for calorie and macro analysis</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Utensils className="h-5 w-5" /> Analyze Food</CardTitle>
        </CardHeader>
        <CardContent>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files?.[0] && analyzeMutation.mutate(e.target.files[0])} />
          <Button onClick={() => fileRef.current?.click()} disabled={analyzeMutation.isPending} className="gap-2">
            {analyzeMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            Upload Food Photo
          </Button>
        </CardContent>
      </Card>

      {data && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader><CardTitle>{data.food_name}</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-xl bg-orange-50 p-4 text-center dark:bg-orange-950/30">
                  <p className="text-2xl font-bold text-orange-600">{data.calories}</p>
                  <p className="text-xs text-slate-500">Calories</p>
                </div>
                <div className="rounded-xl bg-blue-50 p-4 text-center dark:bg-blue-950/30">
                  <p className="text-2xl font-bold text-blue-600">{data.protein}g</p>
                  <p className="text-xs text-slate-500">Protein</p>
                </div>
                <div className="rounded-xl bg-amber-50 p-4 text-center dark:bg-amber-950/30">
                  <p className="text-2xl font-bold text-amber-600">{data.carbs}g</p>
                  <p className="text-xs text-slate-500">Carbs</p>
                </div>
                <div className="rounded-xl bg-red-50 p-4 text-center dark:bg-red-950/30">
                  <p className="text-2xl font-bold text-red-600">{data.fat}g</p>
                  <p className="text-xs text-slate-500">Fat</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Healthy Alternatives</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {data.healthy_alternatives?.map((alt: string, i: number) => (
                <p key={i} className="rounded-lg bg-emerald-50 px-3 py-2 text-sm dark:bg-emerald-950/30">{alt}</p>
              ))}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
