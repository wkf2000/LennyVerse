import { useState } from "react";

import type { GeneratedQuiz } from "../../types/generate";

interface QuizOutputProps {
  quiz: GeneratedQuiz;
}

export default function QuizOutput({ quiz }: QuizOutputProps): JSX.Element {
  const [showModelAnswers, setShowModelAnswers] = useState(false);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">{quiz.title}</h2>
          <p className="mt-2 text-sm text-slate-600">{quiz.total_questions} total questions</p>
        </div>
        <button
          type="button"
          onClick={() => setShowModelAnswers((current) => !current)}
          className="cursor-pointer rounded-full border border-slate-300 bg-white px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-700 transition-colors duration-200 hover:bg-slate-50"
        >
          {showModelAnswers ? "Hide model answers" : "Show model answers"}
        </button>
      </div>

      <div className="mt-5">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Multiple choice</h3>
        <ol className="mt-2 space-y-3">
          {quiz.multiple_choice.map((question) => (
            <li key={`mc-${question.question_number}`} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-medium text-slate-900">
                {question.question_number}. {question.question}
              </p>
              <ul className="mt-2 space-y-1">
                {question.options.map((option) => (
                  <li
                    key={`mc-${question.question_number}-${option.label}`}
                    className={`rounded px-2 py-1 text-sm ${
                      option.label === question.correct_answer ? "bg-emerald-100 text-emerald-800" : "bg-white text-slate-700"
                    }`}
                  >
                    {option.label}. {option.text}
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-slate-500">Source week: {question.source_week}</p>
              <p className="mt-1 text-sm text-slate-700">{question.explanation}</p>
            </li>
          ))}
        </ol>
      </div>

      <div className="mt-6">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Short answer</h3>
        <ol className="mt-2 space-y-3">
          {quiz.short_answer.map((question) => (
            <li key={`sa-${question.question_number}`} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-medium text-slate-900">
                {question.question_number}. {question.question}
              </p>
              <p className="mt-2 text-xs text-slate-500">Source weeks: {question.source_week.join(", ")}</p>
              {showModelAnswers ? (
                <>
                  <p className="mt-2 text-sm text-slate-700">
                    <span className="font-semibold">Model answer:</span> {question.model_answer}
                  </p>
                  <p className="mt-1 text-sm text-slate-700">
                    <span className="font-semibold">Grading guidance:</span> {question.grading_guidance}
                  </p>
                </>
              ) : (
                <p className="mt-2 text-sm text-slate-600">Model answer hidden. Toggle above to reveal.</p>
              )}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
