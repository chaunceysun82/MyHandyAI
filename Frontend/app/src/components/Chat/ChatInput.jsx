import { useState, useEffect, useRef } from "react";
import { detectTools } from "../../services/toolDetection";
import SpeechRecognition, { useSpeechRecognition } from "react-speech-recognition";
import QuickReplyButtons from "./QuickReplyButtons";

export default function ChatInput({ onSend, onDetected, apiBase, showQuickReplies = true }) {
  const [input, setInput] = useState("");
  const [selectedFiles, setSelectedFiles] = useState([]);
  const fileInputRef = useRef(null);
  const [previews, setPreviews] = useState([]);
  const [detecting, setDetecting] = useState(false);
  const [detectError, setDetectError] = useState("");

  const { transcript, listening, resetTranscript, browserSupportsSpeechRecognition } = useSpeechRecognition();

  useEffect(() => {
    if (transcript) setInput(transcript);
  }, [transcript]);

  // Cleanup object URLs when component unmounts
  useEffect(() => {
    return () => {
      previews.forEach(url => url && URL.revokeObjectURL(url));
    };
  }, [previews]);

  // Build previews when selectedFiles changes, and clean up old URLs
  useEffect(() => {
    // clean up old
    previews.forEach(u => u && URL.revokeObjectURL(u));

    const next = selectedFiles.map(f =>
      f.type?.startsWith("image/") ? URL.createObjectURL(f) : null
    );
    setPreviews(next);

    // clean up if the component re-renders/unmounts before next change
    return () => next.forEach(u => u && URL.revokeObjectURL(u));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedFiles]);

  const send = () => {
    if (!input.trim() && selectedFiles.length === 0) return;
    onSend?.(input, selectedFiles);
    setInput("");
    setSelectedFiles([]);      // previews will auto-clean in effect
  };

  const handleQuickReply = (reply) => {
    onSend?.(reply, []);
  };

  const handleMicrophone = () => {
    if (!browserSupportsSpeechRecognition) {
      alert("Browser does not support speech recognition.");
      return;
    }
    if (listening) {
      SpeechRecognition.stopListening();
    } else {
      resetTranscript();
      SpeechRecognition.startListening({
        continuous: false,
        language: "en-US",
      });
    }
  };

  const handleFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleFiles = async (event) => {
    const files = Array.from(event.target.files);
    setSelectedFiles((prev) => [...prev, ...files]);
    
    event.target.value = "";

    // Run tool detection on the first image (if any)
    const first = files.find(f => f.type?.startsWith("image/"));
    if (first) {
      try {
        setDetectError("");
        setDetecting(true);
        const data = await detectTools(first, apiBase);
        onDetected?.(data.tools || []);
      } catch (e) {
        setDetectError(e.message || "Detection failed");
      } finally {
        setDetecting(false);
      }
    }
  };

  const removeFile = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="flex flex-col gap-1">
      {/* Quick Reply Buttons */}
      {showQuickReplies && <QuickReplyButtons onQuickReply={handleQuickReply} />}
      {/* Small detection status */}
      {detecting && (
        <div className="text-xs text-gray-500 px-1">Analyzing image…</div>
      )}
      {!!detectError && (
        <div className="text-xs text-red-500 px-1">{detectError}</div>
      )}

      {/* Selected files preview */}
      {selectedFiles.length > 0 && (
        <div className="flex flex-wrap gap-2 bg-gray-100 rounded-md p-2">
          {selectedFiles.map((file, idx) => (
            <div key={idx} className="relative group">
              {previews[idx] && (
                <div className="w-16 h-16 rounded-lg overflow-hidden border border-gray-300 flex-shrink-0">
                  <img
                    src={previews[idx]}
                    alt={file.name}
                    className="w-full h-full object-cover"
                  />
                  <button
                    onClick={() => removeFile(idx)}
                    className="absolute -top-2 -right-2 w-4 h-4 bg-black text-white rounded-full flex items-center justify-center text-xs font-bold hover:bg-gray-800 transition-colors shadow-md"
                    aria-label="Remove image"
                  >
                    ✕
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center rounded-full bg-[#D9D9D9] border border-gray-200 px-2">
        <button
          className="p-2 text-black"
          onClick={handleFileSelect}
          aria-label="Add photo or file"
          type="button"
        >
          <span className="text-lg">+</span>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFiles}
            multiple
            accept="image/*" // Only allow image files
            className="hidden"
          />
        </button>

        <input
          className="flex-1 bg-transparent px-2 py-2 text-[15px] placeholder:text-[#3A3A3A] focus:outline-none"
          placeholder="Type or speak your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />

        <button
          className={`p-2 text-gray-600 transition-all rounded-xl duration-300 ${
            listening ? "bg-gray-400 animate-pulse" : "hover:bg-gray-200 dark:hover:bg-gray-600"
          }`}
          aria-label="Voice input"
          onClick={handleMicrophone}
          type="button"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="black" aria-hidden="true">
            <path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 14 0h-2zM11 19v3h2v-3h-2z" />
          </svg>
        </button>
      </div>
    </div>
  );
}