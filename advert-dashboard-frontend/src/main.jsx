import React from "react";
import ReactDOM from "react-dom/client";
import Router from "./router";
import "./index.css";          // Tailwind directives live here

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Router />
  </React.StrictMode>
);
