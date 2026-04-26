export type Priority = 'red' | 'yellow' | 'green';

export interface Suggestion {
  question: string;
  reason: string;
  priority: Priority;
  status: string;
  answer_found?: string | null;
  related_diagnoses: string[];
}

export interface Differential {
  diagnosis: string;
  rank: number;
  confidence: number;
  supporting_evidence: string[];
  missing_information: string[];
  suggested_questions: string[];
}

export interface SessionState {
  session_id: string;
  consult_type: string;
  status: string;
  transcript: string;
  suggestions: Suggestion[];
  differentials: Differential[];
  analysis_status: 'pending' | 'ready' | 'failed' | string;
  safety_note: string;
}
