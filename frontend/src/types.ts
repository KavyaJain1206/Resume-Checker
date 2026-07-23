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

export type Confidence = "Verified" | "Estimated" | "Unknown";

export interface JdCategoryScores {
  keywordMatch: number;
  skillsMatch: number;
  educationMatch: number;
  experienceMatch: number;
  certificationMatch: number;
}

export interface JdMatchResult {
  jdMatchScore: number;
  resumeAtsScore: number;
  finalRecommendation: "Strong Match" | "Moderate Match" | "Weak Match";
  categoryScores: JdCategoryScores;
  categoryDetails: Record<keyof JdCategoryScores, string>;
  confidence: {
    experienceMatch: Confidence;
    educationMatch: Confidence;
    certificationMatch: Confidence;
  };
  strengths: string[];
  weaknesses: string[];
  criticalFixes: FixItem[];
  importantTweaks: FixItem[];
  missingKeywords: string[];
  missingSkills: string[];
  atsRisks: string[];
  recruiterView: string;
  topImprovements: string[];
  meta: {
    resumeFileName: string;
    jdFileName: string;
    requiredExperienceYears?: number;
    estimatedExperienceYears?: number;
  };
}
