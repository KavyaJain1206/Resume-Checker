import { useState } from "react";
import IntakePortal from "./components/IntakePortal";
import Scorecard from "./components/Scorecard";
import type { AuditResult, Profile } from "./types";

export default function App() {
  const [result, setResult] = useState<AuditResult | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);

  if (result && profile) {
    return (
      <Scorecard
        result={result}
        profile={profile}
        onReset={() => {
          setResult(null);
          setProfile(null);
        }}
      />
    );
  }
  return (
    <IntakePortal
      onComplete={(r, p) => {
        setResult(r);
        setProfile(p);
      }}
    />
  );
}
