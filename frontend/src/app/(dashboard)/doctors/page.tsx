"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { doctorsApi } from "@/lib/api";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Calendar, Filter, Search, Star, Video } from "lucide-react";
import { useState } from "react";

export default function DoctorsPage() {
  const [search, setSearch] = useState("");
  const [specialty, setSpecialty] = useState("");
  const [onlineOnly, setOnlineOnly] = useState(false);

  const { data: doctors, isLoading } = useQuery({
    queryKey: ["doctors", search, specialty, onlineOnly],
    queryFn: () => doctorsApi.list({ search, specialty, online_only: onlineOnly }).then((r) => r.data),
  });

  const bookMutation = useMutation({
    mutationFn: (doctorId: string) =>
      doctorsApi.book({
        doctor_id: doctorId,
        scheduled_at: new Date(Date.now() + 86400000).toISOString(),
        notes: "Online consultation",
      }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Find a Doctor</h1>
        <p className="text-slate-500">Book appointments with top specialists</p>
      </div>

      <div className="flex flex-wrap gap-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search doctors..."
            className="pl-10"
          />
        </div>
        <Input
          value={specialty}
          onChange={(e) => setSpecialty(e.target.value)}
          placeholder="Specialty"
          className="w-48"
        />
        <Button
          variant={onlineOnly ? "default" : "outline"}
          onClick={() => setOnlineOnly(!onlineOnly)}
          className="gap-2"
        >
          <Filter className="h-4 w-4" /> Online Only
        </Button>
      </div>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-500 border-t-transparent" />
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {doctors?.map((doc: {
            id: string; name: string; specialty: string; experience_years: number;
            rating: number; consultation_fee: number; is_online: boolean; hospital: string;
          }, i: number) => (
            <motion.div key={doc.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
              <Card className="h-full">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-lg">{doc.name}</CardTitle>
                      <CardDescription>{doc.specialty}</CardDescription>
                    </div>
                    {doc.is_online && (
                      <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                        Online
                      </span>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center gap-4 text-sm text-slate-500">
                    <span className="flex items-center gap-1"><Star className="h-3.5 w-3.5 text-amber-500" /> {doc.rating}</span>
                    <span>{doc.experience_years} yrs exp</span>
                  </div>
                  <p className="text-sm text-slate-500">{doc.hospital}</p>
                  <p className="font-semibold text-teal-600">₹{doc.consultation_fee}</p>
                  <div className="flex gap-2">
                    <Button
                      className="flex-1 gap-2"
                      onClick={() => bookMutation.mutate(doc.id)}
                      disabled={bookMutation.isPending}
                    >
                      <Calendar className="h-4 w-4" /> Book
                    </Button>
                    <Button variant="outline" size="icon">
                      <Video className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
