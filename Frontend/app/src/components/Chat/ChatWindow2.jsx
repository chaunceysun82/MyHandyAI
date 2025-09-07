import React, { useEffect, useState, useRef } from "react";
import { createPortal } from "react-dom";
import ChatHeader from "./ChatHeader";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { RotatingLines } from 'react-loader-spinner';

export default function ChatWindow2({
  isOpen,
  onClose,
  projectId,
  URL,
  stepNumber,
  userName // Add userName prop
}) {

  console.log("Project ID:", projectId);
  console.log("Step Number:", stepNumber);

  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(false);
  const [status2, setStatus2] = useState(false);
  const [isClosing, setIsClosing] = useState(false);

  const tips = [
      "💡 Tip: You can upload multiple files for better results.",
      "⚠️ Please be careful when using any tools or materials provided by MyHandyAI.",
      "📂 Keep your project organized for quick access.",
      "💬 Use short and clear prompts for better responses.",
    ];
  
  const [currentTipIndex, setCurrentTipIndex] = useState(0);

  useEffect(() => 
  {
    if (status) {
      const interval = setInterval(() => {
        setCurrentTipIndex((prevIndex) => (prevIndex + 1) % tips.length);
      }, 4500);
      return () => clearInterval(interval);
    }
  }, [status, tips.length]);

  const [drag, setDrag] = useState({ active: false, startY: 0, dy: 0 });
  const THRESHOLD = 120;
  const messagesEndRef = useRef(null);

  const navigate = useNavigate();
  
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  
  // State for suggested messages from backend
  const [suggestedMessages, setSuggestedMessages] = useState([]);

  useEffect(() => {
    if (messagesEndRef.current) 
    {
      messagesEndRef.current.scrollTo({
        top: messagesEndRef.current.scrollHeight,
        behavior: "smooth"
      });
    }
  }, [messages]);

  // Load or start session
  useEffect(() => {
    let cancelled = false;

    const initializeSession = async () => {
      if (cancelled) return;

      try {
        // First, try to get existing session
        const sessionRes = await axios.get(`${URL}/step-guidance/session/${projectId}`);

        if (cancelled) return;

        if (sessionRes.data?.session) {
          // Session exists, load history
          setSessionId(sessionRes.data.session);

          try {
            const historyRes = await axios.get(`${URL}/step-guidance/session/${sessionRes.data.session}/history`);
            if (!cancelled) {
              const formattedMessages = historyRes.data.map(({role, message}) => ({
                sender: role === "user" ? "user" : "bot",
                content: message,
              }));
              setMessages(formattedMessages);
            }
          } catch (historyErr) {
            if (!cancelled) {
              setMessages([{sender: "bot", content: "Failed to load chat history."}]);
            }
          }
        } else {
          try {
            // No session exists, start new one
            const startRes = await axios.post(
              `${URL}/step-guidance/start`,
              { project: projectId },
              { headers: { "Content-Type": "application/json" }}
            );

            if (!cancelled) {
              console.log("Response from starting session:", startRes.data);
              setSessionId(startRes.data.session_id);
              
              // Set suggested messages from backend response
              if (startRes.data.suggested_messages) {
                setSuggestedMessages(startRes.data.suggested_messages);
                console.log("💬 Step guidance suggested messages received:", startRes.data.suggested_messages);
              }
              
              const historyRes = await axios.get(`${URL}/step-guidance/session/${startRes.data.session_id}/history`);
              const formattedMessages = historyRes.data.map(({role, message}) => ({
                sender: role === "user" ? "user" : "bot",
                content: message,
              }));
              console.log("message: ", formattedMessages);
              setMessages(formattedMessages);
            }
          } catch (historyErr) {
            if (!cancelled) {
              setMessages([{sender: "bot", content: "Failed to load chat history."}]);
            }
          }
        }
      } catch (err) {
        console.log("Error during session initialization:", err);
      }
    };

    initializeSession();

    return () => {
      cancelled = true;
    };
  }, [projectId, URL]);

  // Handle close with animation
  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => {
      onClose?.();
      setIsClosing(false);
    }, 300); // Match animation duration
  };

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
  }, [drag.active, drag.dy, drag.startY]);

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
  }, [isOpen]);

  useEffect(() => {
      const getStatus = async () => {
        if(status === true)
        {
          try 
          {
            const response = await axios.post(`${URL}/generation/all/${projectId}`);

            if(response)
            {
              setStatus2(true);
            }
          } catch (err) {
            console.log("Err: ", err);
          }
        }
      }
      getStatus();
  }, [status, navigate]);

  useEffect(() => {
        if(status2 === true)
        {
            const interval = setInterval(async () => {
              try 
              {
                const response = await axios.get(`${URL}/generation/status/${projectId}`);

                if(response)
                {
                  const message = response.data.message;

                  console.log("Message:", message);
                  if(message === "generation completed")
                  {
                    clearInterval(interval);
                    navigate(`/projects/${projectId}/overview`, { state: { userName } });
                  }
                }
              } 
              catch (err) {
                console.log("Err: ", err);
              }
            }, 5000);

            return () => clearInterval(interval);
        }
  }, [status2, navigate]);



  const handleSend = async (text, files = []) => {
    if (!text.trim() && files.length === 0) return;

    let messageContent = text.trim();

    try {
      if (files.length > 0) {
        const fileNames = files.map(f => f.name).join('\n');
        if (messageContent) {
          messageContent = `${messageContent}\nFiles:\n${fileNames}`;
        } else {
          messageContent = `Files: ${fileNames}`;
        }
      }

      const userMsg = { 
        sender: "user", 
        content: messageContent 
      };

      setMessages((prev) => [...prev, userMsg]);

      // Prepare payload for backend (combine text and first image)
      const currInput = text;
      let uploadedimage = null;

      const currFile = files[0];
      if(currFile && currFile.type.startsWith('image/')) {
        uploadedimage = await toBase64(currFile);
      }

      const payload = {
        message: currInput,      
        project: projectId,    
        uploaded_image: uploadedimage, 
        step: stepNumber || -1
      };

      setLoading(true);

      const res = await axios.post(
        `${URL}/step-guidance/chat`,
        payload,
        { 
          headers: 
            { "Content-Type": "application/json" } 
        }
      );

      const botMsg = { sender: "bot", content: res.data.response };

      setLoading(false);

      setMessages((prev) => [...prev, botMsg]);
      
      // Update suggested messages if provided in response
      if (res.data.suggested_messages) {
        setSuggestedMessages(res.data.suggested_messages);
        console.log("💬 Updated step guidance suggested messages:", res.data.suggested_messages);
      }

      // check for the current_state of the response:
      console.log("Current State:", res.data.current_state);
      
      if(res.data.current_state === 'complete') {
        // Wait a bit for the user to read the final message, then show loading
        setTimeout(() => {
          setStatus(true);
        }, 1500);
      }

    } catch (err) {
      setLoading(false);
      console.error("Chat error", err);

      setMessages((prev) => [
        ...prev,
        { sender: "bot", content: "Oops! Something went wrong." },
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

  // Don't render if not open
  if (!isOpen) return null;

  // Calculate drag transform and closing animation
  const dragTransform = drag.active ? `translateY(${drag.dy}px)` : '';
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
          className={`absolute inset-0 bg-black/30 transition-opacity duration-300 ${
            isClosing ? 'opacity-0' : 'opacity-100'
          }`}
          onClick={handleClose}
        />

        {/* Chat Modal */}
        <div
          className={`absolute bottom-0 h-[90svh] md:h-[95vh] left-1/2 w-full max-w-[420px] -translate-x-1/2 px-4 pt-4 pb-0 transition-all duration-300 ease-out ${
            isClosing ? 'animate-slide-down' : 'animate-slide-up'
          }`}
          style={{
            transform: finalTransform,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Chat Container */}
          <div className="mx-auto max-w-[380px] rounded-t-3xl bg-white shadow-2xl flex flex-col h-full overflow-hidden">
            <ChatHeader onClose={handleClose} dragHandleProps={{ onPointerDown: startDrag }} />

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

            {/* Chat Input */}
            <div className="flex-shrink-0 flex flex-col px-4 py-3 gap-2 mb-3">
              <hr className="border-t border-gray-200/70" />
              <ChatInput onSend={handleSend} suggestedMessages={suggestedMessages} />
            </div>

            {/* Navigation Buttons
            <div className="mt-auto grid grid-cols-2 gap-4 px-4 pb-4">
              <button 
                onClick={() => navigate("/home")}
                className="rounded-[8px] font-regular bg-[#D9D9D9] px-4 py-2 text-black-700 hover:bg-gray-300 transition-colors"
              >
                Previous
              </button>

              <button className="rounded-[8px] font-regular bg-[#D9D9D9] px-4 py-2 text-black-700 hover:bg-gray-300 transition-colors">
                Next
              </button>
            </div> */}
          </div>
        </div>
      </div>
    </>,
    document.body
  );
}
