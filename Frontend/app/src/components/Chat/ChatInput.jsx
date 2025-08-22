import { useState, useEffect, useRef } from "react";
import SpeechRecognition, { useSpeechRecognition } from "react-speech-recognition";
import QuickReplyButtons from "./QuickReplyButtons";

export default function ChatInput({ onSend, showQuickReplies = true }) {
  const [input, setInput] = useState("");
  const [selectedFiles, setSelectedFiles] = useState([]);
  const fileInputRef = useRef(null);

  const { transcript, listening, resetTranscript, browserSupportsSpeechRecognition } = useSpeechRecognition();

  useEffect(() => {
    if (transcript) setInput(transcript);
  }, [transcript]);

  const send = () => {
    if (!input.trim() && selectedFiles.length === 0) return;
    onSend?.(input, selectedFiles);
    setInput("");
    setSelectedFiles([]);
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

  const handleFiles = (event) => {
    const files = Array.from(event.target.files);
    setSelectedFiles((prev) => [...prev, ...files]);
    event.target.value = "";
  };

  const removeFile = (index) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="flex flex-col gap-1">
      {/* Quick Reply Buttons */}
      {showQuickReplies && <QuickReplyButtons onQuickReply={handleQuickReply} />}

      {/* Selected files preview */}
      {selectedFiles.length > 0 && (
        <div className="flex flex-col bg-gray-100 rounded-md p-2 space-y-1">
          {selectedFiles.map((file, idx) => (
            <div key={idx} className="flex justify-between items-center text-sm">
              <span className="truncate">{file.name}</span>
              <button onClick={() => removeFile(idx)} className="text-blue-500 font-bold">✕</button>
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
          <span className="text-lg">＋</span>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFiles}
            multiple
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
