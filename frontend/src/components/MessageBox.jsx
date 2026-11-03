import "./MessageBox.css";

const ICONS = { info: "ℹ", error: "✕", warning: "!" };

/**
 * A coloured box for messages: calm blue for "the agent declined",
 * red for errors.
 *
 * Props: variant ("info" | "error" | "warning"), title, children (the message)
 */
export default function MessageBox({ variant = "info", title, children }) {
  return (
    <div className={`message-box message-box--${variant}`} role={variant === "error" ? "alert" : "status"}>
      <span className="message-box__icon" aria-hidden="true">{ICONS[variant]}</span>
      <div>
        {title && <div className="message-box__title">{title}</div>}
        <div className="message-box__body">{children}</div>
      </div>
    </div>
  );
}
