// Frontend/app/src/services/toolDetection.js
const RAW_BASE =
  process.env.REACT_APP_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "";

export async function detectTools(file, apiBase) {
  const base = (apiBase || "").replace(/\/$/, "");
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${base}/chatbot/tools/detect`, {
    method: "POST",
    body: form,
  });

  if (res.status === 404) return { tools: [] }; // quiet fallback until backend is live
  if (!res.ok) throw new Error(`Tool detect failed: ${res.status}`);
  return res.json();
}

