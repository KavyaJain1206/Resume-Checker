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

export interface JdMatchSummary {
  id: string;
  createdAt: string;
  resumeFileName: string;
  jdFileName: string;
  overallMatchScore: number;
  resumeAtsScore: number;
  finalRecommendation: "Strong Match" | "Moderate Match" | "Weak Match";
}

export interface JdMatchDetail {
  id: string;
  createdAt: string;
  resumeArtifact: {
    fileName: string;
    fileUrl: string;
    storagePath: string;
    rawExtractedText: string;
  };
  jdArtifact: {
    fileName: string;
    fileUrl: string;
    storagePath: string;
    rawExtractedText: string;
  };
  analysis: JdMatchResult & { overallMatchScore: number };
  scores: {
    overallMatchScore: number;
    resumeAtsScore: number;
    keywordMatchScore: number;
    skillsMatchScore: number;
    educationMatchScore: number;
    experienceMatchScore: number;
    certificationMatchScore: number;
    responsibilitiesMatchScore: number;
    projectsMatchScore?: number | null;
  };
}

export type Confidence = "Verified" | "Estimated" | "Unknown";

export interface ScoreBreakdownItem {
  percentage: number;
  matchedCount: number;
  totalCount: number;
  confidence: Confidence;
  reasonForDeductions: string;
}

export interface JdCategoryScores {
  keywordMatch: number;
  skillsMatch: number;
  educationMatch: number;
  experienceMatch: number;
  certificationMatch: number;
  responsibilitiesMatch?: number;
  projectsMatch?: number;
}

export interface JdScoreBreakdown {
  overallMatch: ScoreBreakdownItem;
  resumeAtsScore: ScoreBreakdownItem;
  keywordMatch: ScoreBreakdownItem;
  skillsMatch: ScoreBreakdownItem;
  educationMatch: ScoreBreakdownItem;
  experienceMatch: ScoreBreakdownItem;
  certificationMatch: ScoreBreakdownItem;
  responsibilitiesMatch: ScoreBreakdownItem;
  projectsMatch: ScoreBreakdownItem;
}

export interface JdMatchResult {
  jdMatchScore: number;
  overallMatchScore: number;
  resumeAtsScore: number;
  finalRecommendation: "Strong Match" | "Moderate Match" | "Weak Match";
  categoryScores: JdCategoryScores;
  categoryDetails: Record<keyof JdCategoryScores, string>;
  confidence: {
    keywordMatch?: Confidence;
    skillsMatch?: Confidence;
    experienceMatch: Confidence;
    educationMatch: Confidence;
    certificationMatch: Confidence;
    responsibilitiesMatch?: Confidence;
    projectsMatch?: Confidence;
  };
  scoreBreakdown: JdScoreBreakdown;
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
