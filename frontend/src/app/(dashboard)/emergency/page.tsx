"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { emergencyApi } from "@/lib/api";
import { motion } from "framer-motion";
import { AlertTriangle, Hospital, MapPin, Phone } from "lucide-react";
import { useState } from "react";

export default function EmergencyPage() {
  const [triggered, setTriggered] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleEmergency = async () => {
    setLoading(true);
    try {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(async (pos) => {
          await emergencyApi.trigger(pos.coords.latitude, pos.coords.longitude);
          setTriggered(true);
          setLoading(false);
        }, async () => {
          await emergencyApi.trigger();
          setTriggered(true);
          setLoading(false);
        });
      } else {
        await emergencyApi.trigger();
        setTriggered(true);
      }
    } catch {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold">Emergency Services</h1>
        <p className="text-slate-500">Quick access to emergency help</p>
      </div>

      <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
        <Button
          variant="destructive"
          size="lg"
          className="h-32 w-full gap-4 text-xl shadow-2xl shadow-red-500/30"
          onClick={handleEmergency}
          disabled={loading || triggered}
        >
          <AlertTriangle className="h-10 w-10" />
          {triggered ? "Emergency Triggered!" : loading ? "Activating..." : "EMERGENCY SOS"}
        </Button>
      </motion.div>

      {triggered && (
        <Card className="border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/30">
          <CardContent className="p-6 text-center">
            <p className="font-semibold text-red-700 dark:text-red-400">Emergency services have been notified</p>
            <p className="mt-2 text-sm text-red-600">Ambulance: 102 | Your location has been shared</p>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Phone className="h-4 w-4" /> Call Ambulance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <a href="tel:102" className="text-2xl font-bold text-red-600">102</a>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Hospital className="h-4 w-4" /> Nearest Hospital
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-medium">City General Hospital</p>
            <p className="text-sm text-slate-500">1.2 km away</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MapPin className="h-5 w-5" /> Emergency Contacts
          </CardTitle>
          <CardDescription>Your contacts will be notified during SOS</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500">Add emergency contacts in your profile settings</p>
        </CardContent>
      </Card>
    </div>
  );
}
