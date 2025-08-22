// Frontend/app/src/services/toolDetection.js
const RAW_BASE =
  process.env.REACT_APP_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "";

export async function detectTools(file, apiBase) {
  const base = (apiBase || RAW_BASE || "").replace(/\/$/, "");
  if (!base) {
    throw new Error("Missing API base URL for tool detection");
  }

  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${base}/api/tools/detect`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Tool detect failed: HTTP ${res.status} ${text}`);
  }
  return res.json(); // { tools: [...] }
}
