import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./theme.css";

// IonityEdge · K10 installer entrypoint. © Ionity (Pty) Ltd · Policy 986 AED
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
