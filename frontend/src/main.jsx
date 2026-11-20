import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import { setUpNativeShell } from "./services/native.js";
import { loadServerUrl } from "./services/server.js";
import "./styles.css";

// The app reads its saved server address before the first request is made
loadServerUrl()
  .catch(() => {})
  .finally(() => {
    setUpNativeShell();
    ReactDOM.createRoot(document.getElementById("root")).render(
      <React.StrictMode>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </React.StrictMode>,
    );
  });
