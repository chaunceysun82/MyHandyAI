import { useState, useEffect, useRef } from "react";
import SpeechRecognition, { useSpeechRecognition } from "react-speech-recognition";
import QuickReplyButtons from "./QuickReplyButtons";

export default function ChatInput({ onSend, showQuickReplies = true, suggestedMessages = [], disabled = false }) {
  const [input, setInput] = useState("");
  const [selectedFiles, setSelectedFiles] = useState([]);
  const fileInputRef = useRef(null);
  const [previews, setPreviews] = useState([]);
  const [detectError, setDetectError] = useState("");
  const [processingImages, setProcessingImages] = useState(false);

  const { transcript, listening, resetTranscript, browserSupportsSpeechRecognition } = useSpeechRecognition();

  // Image compression function for mobile photos
  const compressImage = (file, maxWidth = 1024, quality = 0.8) => {
    return new Promise((resolve, reject) => {
      // If file is already small enough, return as is
      if (file.size < 1024 * 1024) { // Less than 1MB
        resolve(file);
        return;
      }

      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const img = new Image();
      
      img.onload = () => {
        try {
          // Calculate new dimensions while maintaining aspect ratio
          const ratio = Math.min(maxWidth / img.width, maxWidth / img.height);
          canvas.width = img.width * ratio;
          canvas.height = img.height * ratio;
          
          // Draw and compress
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          canvas.toBlob((blob) => {
            if (blob) {
              // Create a new file with the compressed blob
              const compressedFile = new File([blob], file.name, {
                type: 'image/jpeg',
                lastModified: Date.now()
              });
              resolve(compressedFile);
            } else {
              reject(new Error('Failed to compress image'));
            }
          }, 'image/jpeg', quality);
        } catch (error) {
          reject(error);
        } finally {
          // Clean up
          URL.revokeObjectURL(img.src);
        }
      };
      
      img.onerror = () => {
        URL.revokeObjectURL(img.src);
        reject(new Error('Failed to load image for compression'));
      };
      
      img.src = URL.createObjectURL(file);
    });
  };

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
    if (disabled) return;
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
    
    // Mobile-specific validation
    if (files.length === 0) {
      console.warn("No files selected - possible mobile camera issue");
      return;
    }
    
    setProcessingImages(true);
    
    try {
      // Validate files before processing
      const validFiles = files.filter(file => {
        // Check if file exists and has content
        if (!file || file.size === 0) {
          console.warn("Invalid file detected");
          return false;
        }
        
        // Check if it's an image
        if (!file.type.startsWith("image/")) {
          console.warn(`Skipping non-image file: ${file.name}`);
          return false;
        }
        
        return true;
      });
      
      if (validFiles.length === 0) {
        setDetectError("No valid image files found");
        return;
      }
      
      // Compress images to prevent memory issues
      const compressedFiles = await Promise.all(
        validFiles.map(async (file) => {
          try {
            return await compressImage(file);
          } catch (error) {
            console.error(`Error compressing ${file.name}:`, error);
            // If compression fails, try to use original file if it's small enough
            if (file.size < 2 * 1024 * 1024) { // Less than 2MB
              return file;
            }
            throw error;
          }
        })
      );
      
      // Show warning if some files were filtered out
      if (compressedFiles.length !== files.length) {
        const skippedCount = files.length - compressedFiles.length;
        setDetectError(`${skippedCount} file(s) were skipped due to processing errors.`);
        setTimeout(() => setDetectError(""), 5000);
      }
      
      setSelectedFiles((prev) => [...prev, ...compressedFiles]);
      
    } catch (error) {
      console.error("Error processing files:", error);
      setDetectError("Error processing images. Please try again with smaller files.");
      setTimeout(() => setDetectError(""), 5000);
    } finally {
      setProcessingImages(false);
      event.target.value = "";
    }
  };

  const removeFile = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="flex flex-col gap-1">
      {/* Quick Reply Buttons */}
      {showQuickReplies && <QuickReplyButtons onQuickReply={handleQuickReply} suggestedMessages={suggestedMessages} />}
      {/* Small detection status */}
      {processingImages && (
        <div className="text-xs text-blue-500 px-1">Processing images…</div>
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
          disabled={disabled}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFiles}
            multiple
            accept="image/*,.jpg,.jpeg,.png,.gif,.webp" // Only allow image files with specific extensions
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

        {/* Show send button when there's content, microphone when empty */}
        {input.trim() || selectedFiles.length > 0 ? (
          <button
            className="p-2 text-[#1484A3] hover:bg-[#1484A3] hover:text-white transition-all rounded-xl duration-300"
            aria-label="Send message"
            onClick={send}
            type="button"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        ) : (
          <button
            className={`p-2 text-gray-600 transition-all rounded-xl duration-300 ${
              listening ? "bg-gray-400 animate-pulse" : "hover:bg-gray-200 dark:hover:bg-gray-600"
            } disabled:opacity-50 disabled:cursor-not-allowed`}
            aria-label="Voice input"
            onClick={handleMicrophone}
            type="button"
            disabled={disabled}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="black" aria-hidden="true">
              <path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 14 0h-2zM11 19v3h2v-3h-2z" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}