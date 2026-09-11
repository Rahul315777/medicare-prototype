"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { dashboardApi } from "@/lib/api";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Plus, Users } from "lucide-react";
import { useState } from "react";

export default function FamilyPage() {
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", relation: "self", gender: "", blood_group: "" });

  const { data: profiles, refetch } = useQuery({
    queryKey: ["family-profiles"],
    queryFn: () => dashboardApi.getFamilyProfiles().then((r) => r.data),
  });

  const addMutation = useMutation({
    mutationFn: () => dashboardApi.addFamilyProfile(form),
    onSuccess: () => { refetch(); setShowForm(false); setForm({ name: "", relation: "self", gender: "", blood_group: "" }); },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Family Profiles</h1>
          <p className="text-slate-500">Manage medical history for family members</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)} className="gap-2"><Plus className="h-4 w-4" /> Add Member</Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader><CardTitle>Add Family Member</CardTitle></CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2"><Label>Name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div className="space-y-2">
              <Label>Relation</Label>
              <select value={form.relation} onChange={(e) => setForm({ ...form, relation: e.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900">
                <option value="self">Self</option><option value="father">Father</option><option value="mother">Mother</option>
                <option value="child">Child</option><option value="grandparent">Grandparent</option><option value="spouse">Spouse</option>
              </select>
            </div>
            <div className="space-y-2"><Label>Gender</Label><Input value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })} /></div>
            <div className="space-y-2"><Label>Blood Group</Label><Input value={form.blood_group} onChange={(e) => setForm({ ...form, blood_group: e.target.value })} placeholder="e.g. O+" /></div>
            <Button onClick={() => addMutation.mutate()} className="sm:col-span-2">Save Profile</Button>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {profiles?.map((p: { id: string; name: string; relation: string; blood_group: string; gender: string }) => (
          <Card key={p.id}>
            <CardContent className="flex items-center gap-4 p-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-teal-100 dark:bg-teal-900">
                <Users className="h-6 w-6 text-teal-600" />
              </div>
              <div>
                <p className="font-semibold">{p.name}</p>
                <p className="text-sm capitalize text-slate-500">{p.relation}</p>
                {p.blood_group && <p className="text-xs text-teal-600">{p.blood_group}</p>}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
