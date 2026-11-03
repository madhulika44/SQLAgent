import "./QuestionBox.css";

/**
 * The big question input and the Ask button.
 *
 * The text lives in the parent (App) rather than here, because clicking an
 * example question in the sidebar must be able to fill this box. This is a
 * "controlled input": React state is the single source of truth for its value.
 *
 * Props:
 *   value     - current text
 *   onChange  - called with the new text on every keystroke
 *   onSubmit  - called with the question when the user presses Enter or clicks Ask
 *   loading   - while true, input and button are disabled
 */
export default function QuestionBox({ value, onChange, onSubmit, loading }) {
  function handleSubmit(event) {
    // A <form> submits on Enter automatically; preventDefault stops the page reload.
    event.preventDefault();
    if (value.trim() && !loading) onSubmit(value.trim());
  }

  return (
    <form className="question-box card" onSubmit={handleSubmit}>
      <input
        className="question-box__input"
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Ask a business question, e.g. Which city had the most orders last month?"
        disabled={loading}
        maxLength={1000}
        autoFocus
        aria-label="Your question"
      />
      <button className="question-box__button" type="submit" disabled={loading || !value.trim()}>
        {loading ? "Thinking..." : "Ask"}
      </button>
    </form>
  );
}
