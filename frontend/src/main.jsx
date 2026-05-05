// Điểm vào React: import thư viện DOM client và component gốc App.
import React from "react";
// createRoot là API React 18 để gắn cây component vào một phần tử DOM.
import { createRoot } from "react-dom/client";
// Component giao diện chính của ứng dụng.
import App from "./App.jsx";
// File CSS toàn cục (typography, layout).
import "./App.css";

// Lấy phần tử div#root trong index.html.
const el = document.getElementById("root");
// Tạo root React gắn vào phần tử đó.
const root = createRoot(el);
// Render component App vào DOM (StrictMode bật kiểm tra thêm trong dev).
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
