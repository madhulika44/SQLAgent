// Entry point: mounts the <App /> component into <div id="root"> in index.html.
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

createRoot(document.getElementById("root")).render(
  // StrictMode runs extra checks in development (e.g. effects run twice) to catch bugs early.
  <StrictMode>
    <App />
  </StrictMode>
);
