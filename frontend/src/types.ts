export interface CategoryScores {
  atsSafety: number;
  contactProfessionalism: number;
  sectionHierarchy: number;
  metricQuantification: number;
  verbAndBuzzwordQuality: number;
  projectStrength: number;
  keywordTailoring: number;
  recruiterScan: number;
  summaryQuality: number;
}

export interface FixItem {
  id: string;
  category: string;
  title: string;
  description: string;
  whyItMatters: string;
  location?: string;
  action?: string;
  originalText?: string;
  suggestedFix?: string;
}

export interface AuditResult {
  overallScore: number;
  recruiter7SecScan: "PASS" | "FAIL";
  atsRiskLevel: "LOW" | "MED" | "HIGH";
  categoryScores: CategoryScores;
  criticalFixes: FixItem[];
  importantTweaks: FixItem[];
  keywordGaps: { found: string[]; missingHighPriority: string[] };
  passedChecks: string[];
  meta: {
    targetRole: string;
    experienceLevel: string;
    bulletCount: number;
    pageCount: number;
    fileName: string;
  };
}

export interface Profile {
  fullName: string;
  email: string;
  phone: string;
  location: string;
  college: string;
  degree: string;
  branch: string;
  gradYear: string;
  cgpa: string;
  targetRole: string;
  experienceLevel: string;
  skills: string;
  linkedin: string;
  github: string;
}

export interface CandidateSummary {
  id: string;
  createdAt: string;
  fullName: string;
  email: string;
  college: string;
  targetRole: string;
  experienceLevel: string;
  overallScore: number;
  atsRiskLevel: string;
  recruiter7SecScan: string;
}
