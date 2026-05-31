import React, { useCallback, useEffect, useState, useRef } from "react";
import { createPortal } from "react-dom";
import ChatHeader from "./ChatHeader";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { RotatingLines } from "react-loader-spinner";
import { axiosAuthConfig } from "../../services/api";

export default function ChatWindow({
  isOpen,
  onClose,
  projectId,
  projectName,
  userId,
  userName, // Add userName prop
  URL,
  secondChatStatus,
  stepNumber
}) {
  const [render, setRender] = useState(isOpen);
  const [closing, setClosing] = useState(false);
  const [opening, setOpening] = useState(isOpen);
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(false);
  const [status, setStatus] = useState(false);
  const [status2, setStatus2] = useState(false);

  // Tips while loading
  const tips = [
    "💡 We are now analyzing your project...",
    "💡 Putting  your tailored repair recipe together...this may take a couple of minutes...",
    "💡 Thanks for your patience! Almost done...",
    "💡 Almost there, hang tight! MyHandyAI is gathering the best tools for you..."
  ];
  const [currentTipIndex, setCurrentTipIndex] = useState(0);

  const generatePreviewImage = useCallback(async (messageId) => {
    try {
      console.log("[preview] requesting project preview", {
        projectId,
        endpoint: `${URL}/api/v1/information-gathering-agent/preview/${projectId}`,
      });
      const previewRes = await axios.post(
        `${URL}/api/v1/information-gathering-agent/preview/${projectId}`,
        {},
        axiosAuthConfig({ headers: { "Content-Type": "application/json" } })
      );
      console.log("[preview] response", previewRes.data);
      const previewUrl = previewRes.data?.url;
      if (!previewUrl) {
        console.warn("[preview] no preview URL returned", {
          status: previewRes.data?.status,
          stage: previewRes.data?.stage,
          error: previewRes.data?.error,
        });
      }
      setMessages((prev) =>
        prev.map((message) =>
          message.id === messageId
            ? {
                ...message,
                previewLoading: false,
                images: previewUrl ? [previewUrl] : [],
                content: previewUrl
                  ? `${message.content}\n\nPreview ready. Tap the image to open it larger.`
                  : `${message.content}\n\nI couldn't generate the preview this time, but we can still continue with the project confirmation.`,
              }
            : message
        )
      );
    } catch (error) {
      console.error("[preview] generation request failed", {
        message: error?.message,
        status: error?.response?.status,
        data: error?.response?.data,
      });
      setMessages((prev) =>
        prev.map((message) =>
          message.id === messageId
            ? {
                ...message,
                previewLoading: false,
                content: `${message.content}\n\nI couldn't generate the preview this time, but we can still continue with the project confirmation.`,
              }
            : message
        )
      );
    }
  }, [URL, projectId]);

  useEffect(() => {
    if (status) {
      const interval = setInterval(() => {
        setCurrentTipIndex((i) => (i + 1) % tips.length);
      }, 4500);
      return () => clearInterval(interval);
    }
  }, [status, tips.length]);

  // Which API to talk to
  const api = "api/v1/information-gathering-agent";


  const [drag, setDrag] = useState({ active: false, startY: 0, dy: 0 });
  const THRESHOLD = 120;
  const messagesEndRef = useRef(null);

  const STORAGE_SESSION_KEY = `sessionId_${userId}_${projectId}`;
  const STORAGE_MESSAGES_KEY = `messages_${userId}_${projectId}`;
  const STORAGE_TOOLS_KEY   = `owned_tools_${userId}_${projectId}`;

  const navigate = useNavigate();

  const requestClose = useCallback(() => {
    if (closing) return;

    setClosing(true);
    window.setTimeout(() => {
      onClose?.();
      setClosing(false);
      setRender(false);
    }, 300);
  }, [closing, onClose]);

  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem(STORAGE_MESSAGES_KEY);
    return saved ? JSON.parse(saved) : [];
  });

  const [sessionId, setSessionId] = useState(() => {
    const saved = localStorage.getItem(STORAGE_SESSION_KEY);
    console.log("🚀 ChatWindow Initialized:", {
      hasExistingSession: !!saved,
      sessionId: saved || "No existing session",
      projectId: projectId,
      userId: userId,
      api: "api/v1/information-gathering-agent"
    });
    return saved || null;
  });

  // State for suggested messages from backend
  const [suggestedMessages, setSuggestedMessages] = useState([]);

  // Remember detected tools for this chat (and persist)
  const [ownedTools, setOwnedTools] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_TOOLS_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Autoscroll
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollTo({
        top: messagesEndRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages]);

  // Drag handlers
  const startDrag = (e) => setDrag({ active: true, startY: e.clientY, dy: 0 });
  useEffect(() => {
    if (!drag.active) return;
    const move = (e) =>
      setDrag((d) => ({ ...d, dy: Math.max(0, e.clientY - d.startY) }));
    const up = () => {
      const shouldClose = drag.dy > THRESHOLD;
      setDrag({ active: false, startY: 0, dy: 0 });
      if (shouldClose) requestClose();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
    };
  }, [drag.active, drag.dy, drag.startY, requestClose]);

  // Mount/unmount animation
  useEffect(() => {
    if (isOpen) {
      setRender(true);
      setClosing(false);
      setOpening(true);
      requestAnimationFrame(() =>
        requestAnimationFrame(() => setOpening(false))
      );
    } else if (render) {
      setClosing(true);
    }
  }, [isOpen, render]);

  // Lock scroll + Esc
  useEffect(() => {
    if (!render) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e) => e.key === "Escape" && requestClose();
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [render, requestClose]);

  // Generation status poll (step flow)
  useEffect(() => {
    const getStatus = async () => {
      if (status === true) {
        try {
          const response = await axios.post(
            `${URL}/generation/all/${projectId}`,
            null,
            axiosAuthConfig()
          );
          if (response) setStatus2(true);
        } catch (err) {
          console.log("Err: ", err);
        }
      }
    };
    getStatus();
  }, [status, navigate, URL, projectId]);

  useEffect(() => {
    if (status2 === true) {
      const interval = setInterval(async () => {
        try {
          const response = await axios.get(
            `${URL}/generation/status/${projectId}`,
            axiosAuthConfig()
          );
          if (response) {
            const message = response.data.message;
            if (message === "generation completed") {
              clearInterval(interval);
              navigate(`/projects/${projectId}/overview`, { state: { userId, userName } });
            }
          }
        } catch (err) {
          console.log("Err: ", err);
        }
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [status2, navigate, URL, projectId]);

  // Persist messages/tools locally (exclude images to avoid quota issues)
  useEffect(() => {
    try {
      // Strip images from messages before saving to localStorage (images are stored in backend)
      const messagesWithoutImages = messages.map(({ images, isImageOnly, ...msg }) => ({
        ...msg,
        // Keep a flag that image existed, but don't store the actual image data
        hasImage: !!images && images.length > 0,
      }));
      localStorage.setItem(STORAGE_MESSAGES_KEY, JSON.stringify(messagesWithoutImages));
    } catch (error) {
      // Handle quota exceeded or other storage errors gracefully
      if (error.name === 'QuotaExceededError') {
        console.warn('localStorage quota exceeded, clearing old messages');
        try {
          // Try to clear and save only recent messages (last 50)
          const recentMessages = messages.slice(-50).map(({ images, isImageOnly, ...msg }) => ({
            ...msg,
            hasImage: !!images && images.length > 0,
          }));
          localStorage.setItem(STORAGE_MESSAGES_KEY, JSON.stringify(recentMessages));
        } catch (e) {
          console.error('Failed to save messages to localStorage:', e);
        }
      } else {
        console.error('Error saving messages to localStorage:', error);
      }
    }
  }, [messages, STORAGE_MESSAGES_KEY]);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_TOOLS_KEY, JSON.stringify(ownedTools));
    } catch {}
  }, [ownedTools, STORAGE_TOOLS_KEY]);

  // Load or start session
  useEffect(() => {
    async function loadOrStartSession() {
      setInitializing(true);

      try {
      const sessionRes= await axios.get(`${URL}/${api}/thread/${projectId}`, axiosAuthConfig());
      const conversationStatus = sessionRes.data?.conversation_status;
      
      // Don't initialize if conversation is already COMPLETED
      if (conversationStatus === "COMPLETED") {
        console.log("⚠️ Conversation already COMPLETED, skipping initialize");
        if (sessionRes.data?.thread_id) {
          setSessionId(sessionRes.data.thread_id);
          // Load history instead
          try {
            setLoading(true);
            const historyRes = await axios.get(
              `${URL}/${api}/chat/${sessionRes.data.thread_id}/history`,
              axiosAuthConfig()
            );
            const formattedMessages = historyRes.data.messages.map(
              ({ role, content }) => {
                if (!content || typeof content !== 'string') {
                  return {
                    sender: role === "user" ? "user" : "bot",
                    content: content || "",
                  };
                }
                
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
              }
            );
            setMessages(formattedMessages);
            setLoading(false);
          } catch (err) {
            console.error("Error loading completed conversation history:", err);
            setMessages([{ sender: "bot", content: "Conversation completed. Please check your project overview." }]);
            setLoading(false);
          }
        }
        return;
      }
      
      if (!sessionRes.data?.thread_id) {
        try {
          setLoading(true);
          const res = await axios.post(
            `${URL}/${api}/initialize`,
            // chatbot expects {user, project}; step-guidance ignores user.
            { project_id: projectId },
            axiosAuthConfig({ headers: { "Content-Type": "application/json" } })
          );
           console.log("🆕 New Chat: ", res);
          setSessionId(res.data.thread_id);
          localStorage.setItem(STORAGE_SESSION_KEY, res.data.thread_id);
          setMessages([{ sender: "bot", content: res.data.initial_message }]);
          setLoading(false);
          
          // Set suggested messages from backend response
          // if (res.data.suggested_messages) {
          //   setSuggestedMessages(res.data.suggested_messages);
          //   console.log("💬 Suggested messages received:", res.data.suggested_messages);
          // }
          
          // Save detected tools if any
          // Console log the new session ID
          console.log("🆕 New Chat Session Started:", {
            sessionId: res.data.thread_id,
            api: api,
            projectId: projectId,
            userId: userId,
            //suggestedMessages: res.data.suggested_messages
          });
        } catch (err) {
          console.error("Intro message error", err);
          setMessages([{ sender: "bot", content: "Failed to start chat. Please close and try again." }]);
          setLoading(false);
        }
      } else {
        // Console log the existing session ID
        setLoading(true);
        setSessionId(sessionRes.data.thread_id);
        localStorage.setItem(STORAGE_SESSION_KEY, sessionRes.data.thread_id);
        console.log("🔄 Existing Chat Session Loaded:", {
          sessionId: sessionRes.data.thread_id,
          api: api,
          projectId: projectId,
          userId: userId
        });
        
        try {
          // fetch history from the right API family
          const historyRes = await axios.get(
            `${URL}/${api}/chat/${sessionRes.data.thread_id}/history`,
            axiosAuthConfig()
          );
          const formattedMessages = historyRes.data.messages.map(
            ({ role, content }) => {
              if (!content || typeof content !== 'string') {
                return {
                  sender: role === "user" ? "user" : "bot",
                  content: content || "",
                };
              }
              
              // Check if content contains a base64 image data URL
              const base64ImageRegex = /data:image\/[^;]+;base64,[^\s]+/g;
              const imageMatches = content.match(base64ImageRegex);
              
              if (imageMatches && imageMatches.length > 0) {
                // Extract images and remove them from text
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
              
              // Regular text message
              return {
                sender: role === "user" ? "user" : "bot",
                content: content,
              };
            }
          );
          setMessages(formattedMessages);
          setLoading(false);

        } catch (err) {
          setMessages([{ sender: "bot", content: "Failed to load chat history." }]);
          setLoading(false);
        }
      }
      } catch (err) {
        console.error("Chat session setup error:", err);
        setMessages([{ sender: "bot", content: "Failed to get chat ready. Please close and try again." }]);
        setLoading(false);
      } finally {
        setInitializing(false);
      }
    }
    loadOrStartSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, userId, api]);

  // Send message handler (merged behavior)
  const handleSend = async (text, files = []) => {
    if (!text.trim() && files.length === 0) return;
    if (!sessionId) {
      setMessages((prev) => [
        ...prev,
        { sender: "bot", content: "I am still getting this chat ready. Please try again in a moment." },
      ]);
      return;
    }

    try {
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

      // 1) Show selected images as separate messages (image bubbles)
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

      // 2) Build visible user text (without file names) - only if there's actual text
      let messageContent = text.trim();
      if (messageContent) {
        setMessages((prev) => [...prev, { sender: "user", content: messageContent }]);
      }

      // 3) Add detected-tools hint for the LLM
      const detSummary =
        validFiles.length > 0 && ownedTools.length > 0
          ? `\n\n[Detected tools in attached image: ${ownedTools.map(t => t.name).join(", ")}]`
          : "";
      const currInput = `${messageContent || text || ""}${detSummary}`;

      // 4) Prepare payload per API
      let uploaded_image = null;
      let image_mime_type = null;
      const firstImage = validFiles.find((f) => f.type.startsWith("image/"));
      if (firstImage) {
        try {
          const dataUrl = await toBase64(firstImage);
          // Extract base64 string by splitting on comma (remove data:image/jpeg;base64, prefix)
          // Format: "data:image/jpeg;base64,/9j/4AAQS..." -> "/9j/4AAQS..."
          uploaded_image = dataUrl.split(',')[1];
          
          if (!uploaded_image) {
            throw new Error("Failed to extract base64 string from data URL");
          }
          
          // Use file.type directly for MIME type (more reliable than parsing data URL)
          // Normalize common MIME types to ensure backend compatibility
          let mimeType = firstImage.type || "image/jpeg";
          // Ensure we have a valid MIME type (compression converts to JPEG)
          if (!mimeType || !mimeType.startsWith("image/")) {
            mimeType = "image/jpeg"; // Default fallback
          }
          image_mime_type = mimeType;
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

      let payload;
      let endpoint = `${URL}/${api}/chat/${sessionId}`;
      if (api === "api/v1/information-gathering-agent") {
        payload = {
          text: currInput,
          project_id: projectId,
          thread_id: sessionId,
        };
        
        // Always include image fields together if image exists
        if (uploaded_image) {
          payload.image_base64 = uploaded_image;
          payload.image_mime_type = image_mime_type || "image/jpeg"; // Fallback to jpeg if type is missing
        }
        
        // Debug logging
        if (uploaded_image) {
          console.log("📤 Sending image payload:", {
            has_image: !!uploaded_image,
            image_length: uploaded_image?.length,
            mime_type: payload.image_mime_type,
            image_preview: uploaded_image?.substring(0, 50) + "..."
          });
        }
      } else {
        // step-guidance
        payload = {
          message: currInput,
          project: projectId,
          step: stepNumber || 0,
          uploaded_image,
        };
      }

      // 5) Send
      setLoading(true);
      const res = await axios.post(
        endpoint,
        payload,
        axiosAuthConfig({ headers: { "Content-Type": "application/json" } })
      );

      const shouldGeneratePreview = res.data.preview_image_status === "generating";
      if (res.data.preview_image_status || res.data.preview_image_url) {
        console.log("[preview] chat response preview metadata", {
          status: res.data.preview_image_status,
          hasUrl: Boolean(res.data.preview_image_url),
        });
      }
      const previewImages = res.data.preview_image_url ? [res.data.preview_image_url] : [];
      const botMessageId = `bot-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const botMsg = {
        id: botMessageId,
        sender: "bot",
        content: res.data.preview_image_url || shouldGeneratePreview
          ? `${res.data.agent_response}\n\nHere is a preview of how the finished result could look:`
          : res.data.agent_response,
        images: previewImages,
        previewLoading: shouldGeneratePreview && previewImages.length === 0,
      };
      setLoading(false);
      setMessages((prev) => [...prev, botMsg]);

      if (shouldGeneratePreview && previewImages.length === 0) {
        generatePreviewImage(botMessageId);
      }
      
      // Update suggested messages if provided in response
      if (res.data.suggested_messages) {
        setSuggestedMessages(res.data.suggested_messages);
        console.log("💬 Updated suggested messages:", res.data.suggested_messages);
      }

      // Check conversation status - if COMPLETED, trigger generation pipeline after delay
      if (res.data.conversation_status === "COMPLETED") {
        // Wait 5 seconds for the user to read the final message, then trigger generation
        setTimeout(() => setStatus(true), 5000);
      }
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

  // When ChatInput detects tools, save and show a visible bot note
  function handleDetectedTools(tools) {
    if (!Array.isArray(tools) || tools.length === 0) return;
    setOwnedTools((prev) => {
      const map = new Map(prev.map((t) => [String(t.name || "").toLowerCase(), t]));
      tools.forEach((t) => map.set(String(t.name || "").toLowerCase(), t));
      return Array.from(map.values());
    });
    const summary = tools
      .map((t) => `${t.name}${t.confidence ? ` (${Math.round(t.confidence * 100)}%)` : ""}`)
      .join(", ");
    setMessages((prev) => [
      ...prev,
      { sender: "bot", content: `Detected tools: ${summary}` },
    ]);
  }

  if (!render || typeof document === "undefined") return null;

  const isDragging = drag.active;
  const translateY = closing
    ? "100%"
    : isDragging
    ? `${drag.dy}px`
    : opening
    ? "100%"
    : "0px";

  return createPortal(
    <div className="fixed inset-0 z-[1000]">
      <div
        className={`absolute inset-0 bg-[#07313d]/15 backdrop-blur-[1px] transition-opacity duration-500 ease-out ${
          closing || opening ? "opacity-0" : "opacity-100"
        }`}
        onClick={requestClose}
      />

      <div
        className={`absolute bottom-0 left-1/2 h-[90svh] w-full max-w-[420px] -translate-x-1/2 px-4 pt-4 pb-0 md:h-[95vh] ${
          isDragging ? "transition-none" : "transition-[transform,opacity,filter] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]"
        }`}
        style={{
          transform: `translate(-50%, ${translateY}) ${
            closing || opening ? "scale(0.96)" : "scale(1)"
          }`,
          opacity: closing || opening ? 0 : 1,
          filter: closing || opening ? "blur(2px)" : "blur(0)",
          willChange: "transform, opacity, filter",
        }}
        onClick={(e) => e.stopPropagation()}
        onTransitionEnd={(e) => {
          if (closing && e.target === e.currentTarget) {
            setRender(false);
          }
        }}
      >
        <div className="mx-auto max-w-[380px] rounded-t-3xl bg-[#fffef6] shadow-2xl flex flex-col h-full overflow-hidden">
          <ChatHeader onClose={requestClose} dragHandleProps={{ onPointerDown: startDrag }} />

          {status === false ? (
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
          ) : (
            <div className="flex flex-col items-center justify-center h-full w-full px-4">
              <RotatingLines
                strokeColor="blue"
                strokeWidth="2"
                animationDuration="0.1"
                width="45"
                visible={true}
              />
              <p className="mt-6 text-gray-600 text-sm text-center transition-all duration-500 ease-in-out">
                {tips[currentTipIndex]}
              </p>
            </div>
          )}

          <div className="flex-shrink-0 flex flex-col px-4 py-3 mb-3 gap-2">
            <hr className="border-t border-gray-200/70" />
            <ChatInput
              onSend={handleSend}
              onDetected={handleDetectedTools}
              apiBase={URL}
              suggestedMessages={suggestedMessages}
              disabled={initializing || loading || !sessionId}
            />
          </div>

          {/* <div className="mt-auto grid grid-cols-2 gap-4 px-4 pb-4">
            <button 
          <div className="mt-auto grid grid-cols-2 gap-4 px-4 pb-4">
            <button
              onClick={() => navigate("/home")}
              className="rounded-[8px] font-regular bg-[#D9D9D9] px-4 py-2 text-black-700"
            >
              Previous
            </button>

            <button className="rounded-[8px] font-regular bg-[#D9D9D9] px-4 py-2 text-black-700">
              Next
            </button>

          </div> */}
        </div>
      </div>
    </div>,
    document.body
  );
}
