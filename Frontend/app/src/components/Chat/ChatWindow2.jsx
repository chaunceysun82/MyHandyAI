import React, { useEffect, useState, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import ChatHeader from "./ChatHeader";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";
import axios from "axios";

export default function ChatWindow2({
  isOpen,
  onClose,
  projectId,
  URL,
  stepNumber
}) {
  const [loading, setLoading] = useState(false);
  const [isClosing, setIsClosing] = useState(false);

  const [drag, setDrag] = useState({ active: false, startY: 0, dy: 0 });
  const THRESHOLD = 120;
  const messagesEndRef = useRef(null);

  const [messages, setMessages] = useState([]);
  const [threadId, setThreadId] = useState(null);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollTo({
        top: messagesEndRef.current.scrollHeight,
        behavior: "smooth"
      });
    }
  }, [messages]);

  // Load thread ID and conversation history
  useEffect(() => {
    let cancelled = false;

    const initializeSession = async () => {
      if (cancelled) return;

      try {
        setLoading(true);
        
        // Get thread ID from project assistant agent (same thread as information gathering agent)
        const threadRes = await axios.get(`${URL}/api/v1/project-assistant-agent/thread/${projectId}`);
        
        if (cancelled) return;

        if (threadRes.data?.thread_id) {
          const threadIdValue = threadRes.data.thread_id;
          setThreadId(threadIdValue);

          try {
            // Always initialize the conversation when opening the chat component
            // This ensures a contextual greeting based on the current step_number
            await axios.post(
              `${URL}/api/v1/project-assistant-agent/initialize`,
              {
                thread_id: threadIdValue,
                project_id: projectId,
                step_number: stepNumber !== undefined ? stepNumber : null
              }
            );
            
            if (cancelled) return;

            // Load conversation history from project assistant agent
            // This will include the new initial exchange we just created
            const historyRes = await axios.get(
              `${URL}/api/v1/project-assistant-agent/chat/${threadIdValue}/history`
            );
            
            if (!cancelled) {
              const historyMessages = historyRes.data.messages || [];
              
              // Format existing history messages
              const formattedMessages = historyMessages.map(({ role, content }) => {
                // Handle image content (base64 data URLs)
                const base64ImageRegex = /data:image\/[^;]+;base64,[^\s]+/g;
                const imageMatches = content.match(base64ImageRegex);
                
                if (imageMatches && imageMatches.length > 0) {
                  const images = imageMatches;
                  let textContent = content;
                  
                  // Remove all image data URLs from the text
                  imageMatches.forEach(img => {
                    textContent = textContent.replace(img, '').trim();
                  });
                  
                  return {
                    sender: role === "user" ? "user" : "bot",
                    content: textContent,
                    images: images,
                    isImageOnly: !textContent || textContent.length === 0,
                  };
                }
                
                return {
                  sender: role === "user" ? "user" : "bot",
                  content: content,
                };
              });
              setMessages(formattedMessages);
            }
          } catch (err) {
            if (!cancelled) {
              console.error("Error during initialization or loading history:", err);
              // If initialization fails, try to load existing history as fallback
              try {
                const historyRes = await axios.get(
                  `${URL}/api/v1/project-assistant-agent/chat/${threadIdValue}/history`
                );
                
                if (!cancelled) {
                  const historyMessages = historyRes.data.messages || [];
                  
                  if (historyMessages.length > 0) {
                    const formattedMessages = historyMessages.map(({ role, content }) => {
                      const base64ImageRegex = /data:image\/[^;]+;base64,[^\s]+/g;
                      const imageMatches = content.match(base64ImageRegex);
                      
                      if (imageMatches && imageMatches.length > 0) {
                        const images = imageMatches;
                        let textContent = content;
                        imageMatches.forEach(img => {
                          textContent = textContent.replace(img, '').trim();
                        });
                        
                        return {
                          sender: role === "user" ? "user" : "bot",
                          content: textContent,
                          images: images,
                          isImageOnly: !textContent || textContent.length === 0,
                        };
                      }
                      
                      return {
                        sender: role === "user" ? "user" : "bot",
                        content: content,
                      };
                    });
                    setMessages(formattedMessages);
                  } else {
                    setMessages([{ 
                      sender: "bot", 
                      content: "Failed to initialize chat. Please try again." 
                    }]);
                  }
                }
              } catch (historyErr) {
                console.error("Error loading history as fallback:", historyErr);
                if (!cancelled) {
                  setMessages([{ 
                    sender: "bot", 
                    content: "Failed to load chat. Please try again." 
                  }]);
                }
              }
            }
          }
        } else {
          // No thread exists yet - user needs to start with information gathering agent first
          if (!cancelled) {
            setMessages([{ 
              sender: "bot", 
              content: "Please start a conversation with the information gathering agent first to begin your project." 
            }]);
          }
        }
      } catch (err) {
        console.error("Error during session initialization:", err);
        if (!cancelled) {
          setMessages([{ sender: "bot", content: "Failed to initialize chat. Please try again." }]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    if (isOpen && projectId) {
      initializeSession();
    }

    return () => {
      cancelled = true;
    };
  }, [projectId, URL, isOpen, stepNumber]);

  // Handle close with animation
  const handleClose = useCallback(() => {
    setIsClosing(true);
    setTimeout(() => {
      onClose?.();
      setIsClosing(false);
    }, 300);
  }, [onClose]);

  // Drag handlers
  const startDrag = (e) => setDrag({ active: true, startY: e.clientY, dy: 0 });

  useEffect(() => {
    if (!drag.active) return;
    const move = (e) => setDrag((d) => ({ ...d, dy: Math.max(0, e.clientY - d.startY) }));
    const up = () => {
      const shouldClose = drag.dy > THRESHOLD;
      setDrag({ active: false, startY: 0, dy: 0 });
      if (shouldClose) handleClose();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
    };
  }, [drag.active, drag.dy, drag.startY, handleClose]);

  // Lock scroll + Esc
  useEffect(() => {
    if (!isOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e) => e.key === "Escape" && handleClose();
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [isOpen, handleClose]);


  const handleSend = async (text, files = []) => {
    // Prevent sending if already loading or no thread ID
    if (loading || !threadId) {
      return;
    }

    if (!text.trim() && files.length === 0) return;

    // Validate files before processing
    const validFiles = files.filter(file => {
      if (!file.type.startsWith("image/")) {
        console.warn(`Skipping non-image file: ${file.name}`);
        return false;
      }

      // Check file size (limit to 5MB)
      const maxSize = 5 * 1024 * 1024; // 5MB
      if (file.size > maxSize) {
        console.warn(`File too large: ${file.name} (${file.size} bytes)`);
        return false;
      }

      return true;
    });

    if (validFiles.length !== files.length) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          content: "Some files were skipped due to size limits (max 5MB) or invalid format (images only)."
        },
      ]);
    }

    // Show selected images as separate messages (image bubbles)
    if (validFiles.length > 0) {
      for (const file of validFiles) {
        try {
          const imageUrl = await toBase64(file);
          const imageMsg = {
            sender: "user",
            content: "",
            images: [imageUrl],
            isImageOnly: true,
          };
          setMessages((prev) => [...prev, imageMsg]);
        } catch (error) {
          console.error("Error processing image:", error);
          setMessages((prev) => [
            ...prev,
            {
              sender: "bot",
              content: `Error processing image ${file.name}: ${error.message}`
            },
          ]);
        }
      }
    }

    const messageContent = text.trim();

    try {
      // Only create text message if there's actual content
      if (messageContent) {
        const userMsg = {
          sender: "user",
          content: messageContent
        };
        setMessages((prev) => [...prev, userMsg]);
      }

      // Prepare payload for backend
      let image_base64 = null;
      let image_mime_type = null;

      const currFile = validFiles[0];
      if (currFile && currFile.type.startsWith('image/')) {
        try {
          const dataUrl = await toBase64(currFile);
          // Extract base64 string (remove data:image/jpeg;base64, prefix)
          image_base64 = dataUrl.split(',')[1];
          image_mime_type = currFile.type || "image/jpeg";
        } catch (error) {
          console.error("Error converting image to base64:", error);
          setMessages((prev) => [
            ...prev,
            { 
              sender: "bot", 
              content: "Error processing image. Please try again with a smaller file or different image format." 
            },
          ]);
          setLoading(false);
          return;
        }
      }

      const payload = {
        project_id: projectId,
        text: messageContent || null,
        image_base64: image_base64,
        image_mime_type: image_mime_type,
        step_number: stepNumber !== undefined ? stepNumber : null
      };

      setLoading(true);

      const res = await axios.post(
        `${URL}/api/v1/project-assistant-agent/chat/${threadId}`,
        payload,
        {
          headers: { "Content-Type": "application/json" }
        }
      );

      const botMsg = { sender: "bot", content: res.data.agent_response };

      setLoading(false);
      setMessages((prev) => [...prev, botMsg]);

    } catch (err) {
      setLoading(false);
      console.error("Chat error", err);
      setMessages((prev) => [
        ...prev,
        { sender: "bot", content: "Oops! Something went wrong. Please try again." },
      ]);
    }
  };

  const toBase64 = (file) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = () => {
        try {
          const result = reader.result;
          // Clean up immediately to prevent memory leaks
          reader.onload = null;
          reader.onerror = null;
          reader.onabort = null;
          resolve(result);
        } catch (error) {
          reject(error);
        }
      };
      
      reader.onerror = (error) => {
        reader.onload = null;
        reader.onerror = null;
        reader.onabort = null;
        reject(error);
      };
      
      reader.onabort = () => {
        reader.onload = null;
        reader.onerror = null;
        reader.onabort = null;
        reject(new Error('File reading was aborted'));
      };
      
      try {
        reader.readAsDataURL(file);
      } catch (error) {
        reject(error);
      }
    });

  // Don't render if not open
  if (!isOpen) return null;

  // Calculate drag transform and closing animation
  const closingTransform = isClosing ? 'translate(-50%, 100%)' : 'translate(-50%, 0px)';
  const finalTransform = drag.active ? `translate(-50%, ${drag.dy}px)` : closingTransform;

  return createPortal(
    <>
      <style>
        {`
          @keyframes slideUp {
            from {
              transform: translate(-50%, 100%);
            }
            to {
              transform: translate(-50%, 0px);
            }
          }
          
          @keyframes slideDown {
            from {
              transform: translate(-50%, 0px);
            }
            to {
              transform: translate(-50%, 100%);
            }
          }
          
          .animate-slide-up {
            animation: slideUp 0.3s ease-out forwards;
          }
          
          .animate-slide-down {
            animation: slideDown 0.3s ease-out forwards;
          }
        `}
      </style>

      <div className="fixed inset-0 z-[1000]">
        {/* Backdrop */}
        <div
          className={`absolute inset-0 bg-black/30 transition-opacity duration-300 ${isClosing ? 'opacity-0' : 'opacity-100'
            }`}
          onClick={handleClose}
        />

        {/* Chat Modal */}
        <div
          className={`absolute bottom-0 h-[90svh] md:h-[95vh] left-1/2 w-full max-w-[420px] -translate-x-1/2 px-4 pt-4 pb-0 transition-all duration-300 ease-out ${isClosing ? 'animate-slide-down' : 'animate-slide-up'
            }`}
          style={{
            transform: finalTransform,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Chat Container */}
          <div className="mx-auto max-w-[380px] rounded-t-3xl bg-white shadow-2xl flex flex-col h-full overflow-hidden">
            <ChatHeader onClose={handleClose} dragHandleProps={{ onPointerDown: startDrag }} />

            <div
              ref={messagesEndRef}
              className="flex-1 overflow-y-auto px-5 pt-1 pb-3 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
            >
              <MessageList messages={messages} />

              {loading && (
                <div className="flex items-center gap-2 text-gray-500 mt-2">
                  <div className="loader w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin"></div>

                  <div className="flex items-center gap-1">
                    <span>Bot is thinking</span>
                    <div className="flex items-center gap-1 translate-y-[4px]">
                      <span className="w-1 h-1 bg-gray-400 rounded-full animate-typing-wave"></span>
                      <span className="w-1 h-1 bg-gray-400 rounded-full animate-typing-wave [animation-delay:0.2s]"></span>
                      <span className="w-1 h-1 bg-gray-400 rounded-full animate-typing-wave [animation-delay:0.4s]"></span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Chat Input */}
            <div className="flex-shrink-0 flex flex-col px-4 py-3 gap-2 mb-3">
              <hr className="border-t border-gray-200/70" />
              <ChatInput 
                onSend={handleSend} 
                disabled={loading || !threadId}
              />
            </div>
          </div>
        </div>
      </div>
    </>,
    document.body
  );
}
