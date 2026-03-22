import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { KnowledgeGalaxyPage } from "@/pages/KnowledgeGalaxyPage";
import "@/styles/styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <KnowledgeGalaxyPage />
  </StrictMode>,
);
