import React, { useEffect, useState, useRef } from "react";
import { createPortal } from "react-dom";
import ChatHeader from "./ChatHeader";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { RotatingLines } from "react-loader-spinner";

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
  const [opening, setOpening] = useState(false);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(false);
  const [status2, setStatus2] = useState(false);

  // Tips while loading
  const tips = [
    "💡 Tip: You can upload multiple files for better results.",
    "⚠️ Please be careful when using any tools or materials provided by MyHandyAI.",
    "📂 Keep your project organized for quick access.",
    "💬 Use short and clear prompts for better responses.",
  ];
  const [currentTipIndex, setCurrentTipIndex] = useState(0);
  useEffect(() => {
    if (status) {
      const interval = setInterval(() => {
        setCurrentTipIndex((i) => (i + 1) % tips.length);
      }, 4500);
      return () => clearInterval(interval);
    }
  }, [status, tips.length]);

  // Which API to talk to
  const api = secondChatStatus ? "step-guidance" : "chatbot";

  // Step-guidance bootstrap flag
  const [bool, setBool] = useState(null);
  useEffect(() => {
    const check = async () => {
      try {
        const res = await axios.get(`${URL}/step-guidance/started/${projectId}`);
        if (res.data) setBool(res.data);
      } catch (err) {
        console.error("Error checking step guidance status:", err);
      }
    };
    check();
  }, [URL, projectId]);

  const [drag, setDrag] = useState({ active: false, startY: 0, dy: 0 });
  const THRESHOLD = 120;
  const messagesEndRef = useRef(null);

  const STORAGE_SESSION_KEY = `sessionId_${userId}_${projectId}`;
  const STORAGE_MESSAGES_KEY = `messages_${userId}_${projectId}`;
  const STORAGE_TOOLS_KEY   = `owned_tools_${userId}_${projectId}`;

  const navigate = useNavigate();

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
      api: secondChatStatus ? "step-guidance" : "chatbot"
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
      if (shouldClose) onClose?.();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
    };
  }, [drag.active, drag.dy, drag.startY, onClose]);

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
    const onKey = (e) => e.key === "Escape" && onClose?.();
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [render, onClose]);

  // Generation status poll (step flow)
  useEffect(() => {
    const getStatus = async () => {
      if (status === true) {
        try {
          const response = await axios.post(`${URL}/generation/all/${projectId}`);
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
          const response = await axios.get(`${URL}/generation/status/${projectId}`);
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

  // Persist messages/tools locally
  useEffect(() => {
    localStorage.setItem(STORAGE_MESSAGES_KEY, JSON.stringify(messages));
  }, [messages, STORAGE_MESSAGES_KEY]);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_TOOLS_KEY, JSON.stringify(ownedTools));
    } catch {}
  }, [ownedTools, STORAGE_TOOLS_KEY]);

  // Load or start session
  useEffect(() => {
    async function loadOrStartSession() {
      if (!sessionId) {
        try {
          const res = await axios.post(
            `${URL}/${api}/start`,
            // chatbot expects {user, project}; step-guidance ignores user.
            { user: userId, project: projectId },
            { headers: { "Content-Type": "application/json" } }
          );
          setSessionId(res.data.session_id);
          localStorage.setItem(STORAGE_SESSION_KEY, res.data.session_id);
          setMessages([{ sender: "bot", content: res.data.intro_message }]);
          
          // Set suggested messages from backend response
          if (res.data.suggested_messages) {
            setSuggestedMessages(res.data.suggested_messages);
            console.log("💬 Suggested messages received:", res.data.suggested_messages);
          }
          
          // Console log the new session ID
          console.log("🆕 New Chat Session Started:", {
            sessionId: res.data.session_id,
            api: api,
            projectId: projectId,
            userId: userId,
            suggestedMessages: res.data.suggested_messages
          });
        } catch (err) {
          console.error("Intro message error", err);
        }
      } else {
        // Console log the existing session ID
        console.log("🔄 Existing Chat Session Loaded:", {
          sessionId: sessionId,
          api: api,
          projectId: projectId,
          userId: userId
        });
        
        try {
          // fetch history from the right API family
          const historyRes = await axios.get(
            `${URL}/${api}/session/${sessionId}/history`
          );
          const formattedMessages = historyRes.data.map(
            ({ role, message }) => ({
              sender: role === "user" ? "user" : "bot",
              content: message,
            })
          );
          setMessages(formattedMessages);

          // If step-guidance mode and not started, kick it off using the existing session
          if (secondChatStatus && !bool) {
            const res = await axios.post(
              `${URL}/${api}/start`,
              { project: projectId, session_id: sessionId },
              { headers: { "Content-Type": "application/json" } }
            );
            setSessionId(res.data.session_id);
            localStorage.setItem(STORAGE_SESSION_KEY, res.data.session_id);
            setMessages((prev) => [
              ...prev,
              { sender: "bot", content: res.data.response },
            ]);
          }
        } catch (err) {
          setMessages([{ sender: "bot", content: "Failed to load chat history." }]);
        }
      }
    }
    loadOrStartSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, userId, api]);

  // Send message handler (merged behavior)
  const handleSend = async (text, files = []) => {
    if (!text.trim() && files.length === 0) return;

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

      // 2) Build visible user text + file list
      let messageContent = text.trim();
      if (validFiles.length > 0) {
        const fileNames = validFiles.map((f) => f.name).join("\n");
        messageContent = messageContent
          ? `${messageContent}\nFiles:\n${fileNames}`
          : `Files: ${fileNames}`;
      }
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
      const firstImage = validFiles.find((f) => f.type.startsWith("image/"));
      if (firstImage) {
        try {
          uploaded_image = await toBase64(firstImage);
        } catch (error) {
          console.error("Error converting image to base64:", error);
          setMessages((prev) => [
            ...prev,
            { 
              sender: "bot", 
              content: "Error processing image. Please try again with a smaller file." 
            },
          ]);
          return;
        }
      }

      let payload;
      let endpoint = `${URL}/${api}/chat`;
      if (api === "chatbot") {
        payload = {
          message: currInput,
          user: userId,
          project: projectId,
          session_id: sessionId,
          uploaded_image,
          owned_tools: ownedTools,
        };
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
      const res = await axios.post(endpoint, payload, {
        headers: { "Content-Type": "application/json" },
      });

      const botMsg = { sender: "bot", content: res.data.response };
      setLoading(false);
      setMessages((prev) => [...prev, botMsg]);
      
      // Update suggested messages if provided in response
      if (res.data.suggested_messages) {
        setSuggestedMessages(res.data.suggested_messages);
        console.log("💬 Updated suggested messages:", res.data.suggested_messages);
      }

      if (res.data.current_state === "complete") {
        // Wait longer for the user to read the final message, then show loading
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
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result);
      reader.onerror = (error) => reject(error);
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
        className={`absolute inset-0 bg-gray-200 transition-opacity duration-300 ${
          closing ? "opacity-0" : "opacity-100"
        }`}
      />

      <div
        className={`absolute bottom-0 h-screen left-1/2 w-full max-w-[420px] -translate-x-1/2 px-4 pb-0 ${
          isDragging ? "transition-none" : "transition-[transform,opacity] duration-300 ease-out"
        }`}
        style={{
          transform: `translate(-50%, ${translateY}) ${closing ? "scale(0.98)" : "scale(1)"}`,
          opacity: closing ? 0.98 : 1,
          willChange: "transform, opacity",
        }}
        onClick={(e) => e.stopPropagation()}
        onTransitionEnd={(e) => {
          if (closing && e.target === e.currentTarget) {
            setRender(false);
            setClosing(false);
          }
        }}
      >
        <div className="mx-auto max-w-[380px] bg-[#fffef6] shadow-md flex flex-col h-full overflow-hidden">
          <ChatHeader onClose={onClose} dragHandleProps={{ onPointerDown: startDrag }} />

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
            <div className="flex flex-col items-center justify-center h-screen w-full px-4">
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
