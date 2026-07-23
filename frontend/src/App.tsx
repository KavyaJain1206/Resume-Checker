import { useState } from "react";
import IntakePortal from "./components/IntakePortal";
import Scorecard, { JdScorecard } from "./components/Scorecard";
import type { AuditResult, JdMatchResult, Profile } from "./types";

export default function App() {
  const [result, setResult] = useState<AuditResult | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [jdResult, setJdResult] = useState<JdMatchResult | null>(null);

  if (jdResult) {
    return <JdScorecard result={jdResult} onReset={() => setJdResult(null)} />;
  }
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
      onJdComplete={(r) => setJdResult(r)}
    />
  );
}
