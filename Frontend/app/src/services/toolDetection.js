// Frontend/app/src/services/toolDetection.js
const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || process.env.REACT_APP_API_BASE_URL;

export async function detectTools(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/tools/detect`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Detect failed: ${res.status} ${text}`);
  }
  return res.json(); // -> { tools: [{ name, confidence, notes? }] }
}
