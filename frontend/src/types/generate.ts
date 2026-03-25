export type DifficultyLevel = "intro" | "intermediate" | "advanced";

export interface OutlineRequest {
  topic: string;
  num_weeks?: number;
  difficulty?: DifficultyLevel;
}

export interface ReadingRef {
  content_id: string;
  title: string;
  content_type: string;
  relevance_summary: string;
}

export interface WeekOutline {
  week_number: number;
  theme: string;
  description: string;
  readings: ReadingRef[];
}

export interface OutlineResponse {
  topic: string;
  num_weeks: number;
  difficulty: DifficultyLevel | string;
  weeks: WeekOutline[];
  corpus_coverage: string;
  low_coverage: boolean;
}

export interface ExecuteRequest {
  topic: string;
  num_weeks: number;
  difficulty: DifficultyLevel | string;
  approved_outline: WeekOutline[];
}

export interface GeneratedReading {
  content_id: string;
  title: string;
  content_type: string;
  key_concepts: string[];
  notable_quotes: string[];
  discussion_hooks: string[];
}

export interface GeneratedWeek {
  week_number: number;
  theme: string;
  status: "complete" | "incomplete";
  learning_objectives: string[];
  narrative_summary: string;
  readings: GeneratedReading[];
  key_takeaways: string[];
}

export interface GeneratedSyllabus {
  topic: string;
  difficulty: string;
  weeks: GeneratedWeek[];
}

export interface QuizOption {
  label: string;
  text: string;
}

export interface MultipleChoiceQuestion {
  question_number: number;
  question: string;
  options: QuizOption[];
  correct_answer: string;
  explanation: string;
  source_week: number;
}

export interface ShortAnswerQuestion {
  question_number: number;
  question: string;
  model_answer: string;
  grading_guidance: string;
  source_week: number[];
}

export interface GeneratedQuiz {
  title: string;
  total_questions: number;
  multiple_choice: MultipleChoiceQuestion[];
  short_answer: ShortAnswerQuestion[];
}

export interface StepLogPayload {
  node: "retrieve_deep_context" | "generate_weeks" | "generate_quiz" | "format_output" | string;
  status: "running" | "done" | "error";
  message: string;
  week?: number | null;
}

export interface GenerateResultPayload {
  syllabus: GeneratedSyllabus;
  quiz: GeneratedQuiz;
}

export interface GenerateDonePayload {
  total_duration_ms: number;
  weeks_generated: number;
  quiz_questions: number;
}

export interface GenerateErrorPayload {
  message: string;
  retriable: boolean;
}

export type GenerateSseEvent =
  | { type: "step_log"; payload: StepLogPayload }
  | { type: "result"; payload: GenerateResultPayload }
  | { type: "error"; payload: GenerateErrorPayload }
  | { type: "done"; payload: GenerateDonePayload };
