import { useEffect, useState } from "react";
import "./LoadingSteps.css";

// What the agent does, in order (see backend/app/agent.py).
const STEPS = ["Loading schema", "Asking the LLM", "Validating SQL", "Running query"];
const STEP_INTERVAL_MS = 1100;

/**
 * Animated list of agent steps shown while waiting for POST /ask.
 *
 * Honest note: the backend answers in ONE response, so we can't know which
 * step it is on right now. We advance through the steps on a timer to show
 * the audience what is happening, and stop on the last one until the answer
 * arrives. The REAL step-by-step timings appear afterwards in the Trace tab.
 */
export default function LoadingSteps() {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveIndex((i) => Math.min(i + 1, STEPS.length - 1));
    }, STEP_INTERVAL_MS);
    return () => clearInterval(timer); // stop the timer when the component disappears
  }, []);

  return (
    <div className="loading-steps card" role="status" aria-live="polite">
      {STEPS.map((label, index) => {
        const state = index < activeIndex ? "done" : index === activeIndex ? "active" : "pending";
        return (
          <div key={label} className={`loading-step loading-step--${state}`}>
            <span className="loading-step__icon">{state === "done" ? "✓" : index + 1}</span>
            <span className="loading-step__label">{label}</span>
          </div>
        );
      })}
    </div>
  );
}
