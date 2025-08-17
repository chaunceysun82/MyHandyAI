import React, { useEffect, useState, useRef } from "react";
import { createPortal } from "react-dom";
import ChatHeader from "./ChatHeader";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";
import axios from "axios";
import { useNavigate } from "react-router-dom";

export default function ChatWindow({
  isOpen,
  onClose,
  projectId,
  projectName,
  userId,
  URL,
}) {
  const [render, setRender] = useState(isOpen);
  const [closing, setClosing] = useState(false);
  const [opening, setOpening] = useState(false);
  const [loading, setLoading] = useState(false);


  const [drag, setDrag] = useState({ active: false, startY: 0, dy: 0 });
  const THRESHOLD = 120;
  const messagesEndRef = useRef(null);

  const STORAGE_SESSION_KEY = `sessionId_${userId}_${projectId}`;
  const STORAGE_MESSAGES_KEY = `messages_${userId}_${projectId}`;

  const navigate = useNavigate();
  
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem(STORAGE_MESSAGES_KEY);
    return saved ? JSON.parse(saved) : [];
  });

  const [sessionId, setSessionId] = useState(
    localStorage.getItem(STORAGE_SESSION_KEY) || ""
  );

  useEffect(() => {
	if (messagesEndRef.current) 
	{
		messagesEndRef.current.scrollTo({
			top: messagesEndRef.current.scrollHeight,
			behavior: "smooth"
		});
	}
   }, [messages]);
  
  

  // Drag handlers
  const startDrag = (e) => setDrag({ active: true, startY: e.clientY, dy: 0 });
  useEffect(() => {
    if (!drag.active) return;
    const move = (e) => setDrag((d) => ({ ...d, dy: Math.max(0, e.clientY - d.startY) }));
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
      requestAnimationFrame(() => requestAnimationFrame(() => setOpening(false)));
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

  // Persist messages locally
  useEffect(() => {
    localStorage.setItem(STORAGE_MESSAGES_KEY, JSON.stringify(messages));
  }, [messages, STORAGE_MESSAGES_KEY]);


  // Load or start session
  useEffect(() => {
    async function loadOrStartSession() {
      if(!sessionId)
      {
        try {
          const res = await axios.post(
            `${URL}/chatbot/start`,
            { user: userId, project: projectId },
            { headers: { "Content-Type": "application/json" } 
          });
          setSessionId(res.data.session_id);
          localStorage.setItem(STORAGE_SESSION_KEY, res.data.session_id);
          setMessages([{ sender: "bot", content: res.data.intro_message }]);
        } catch (err) 
        {
          console.error("Intro message error", err);
        }
      } else {
        try {
          const historyRes = await axios.get(`${URL}/chatbot/session/${sessionId}/history`);
          const formattedMessages = historyRes.data.map(({role, message}) => ({
            sender: role === "user" ? "user" : "bot",
            content: message,
          }));
          setMessages(formattedMessages);
        } catch (err) {
          setMessages([{sender: "bot", content: "Failed to load chat history."}]);
        }
      }
    }
    loadOrStartSession();
  }, [projectId, userId]);


  // Send message handler
//   const handleSend = async (text, files = []) => {
//     if (!text.trim() && files.length === 0) return;

//     let messageContent = text.trim();
//     if (files.length > 0) {
//       const fileNames = files.map((f) => f.name).join(", ");
//       messageContent = messageContent ? `${messageContent}\n\nFiles: ${fileNames}` : `Files: ${fileNames}`;
//     }

//     // Add user message locally
//     setMessages((prev) => [...prev, { sender: "user", content: messageContent }]);

//     try {
//       const formData = new FormData();
//       formData.append("message", text);
//       formData.append("user", userId);
//       formData.append("project", projectId);
//       formData.append("session_id", sessionId);
//       files.forEach((f, i) => formData.append(`file_${i}`, f));

//       const res = await axios.post(`${URL}/chatbot/chat`, formData, {
//         headers: { "Content-Type": "multipart/form-data" },
//       });

//       setMessages((prev) => [...prev, { sender: "bot", content: res.data.response }]);
//     } catch (err) {
//       console.error("Chat error", err);
//       setMessages((prev) => [...prev, { sender: "bot", content: "Oops! Something went wrong." }]);
//     }
//   };

const handleSend = async (text, files = []) => {
    if (!text.trim() && files.length === 0) return;


    let messageContent = text.trim();
    
    if (files.length > 0) 
    {
      const fileNames = files.map(f => f.name).join('\n');
      if (messageContent) {
        messageContent = `${messageContent}\nFiles:\n${fileNames}`;
      } 
      else 
      {
        messageContent = `Files: ${fileNames}`;
      }
    }


    const userMsg = { 
      sender: "user", 
      content: messageContent 
    };

    setMessages((prev) => [...prev, userMsg]);

    const currInput = text;
    const currFile = files[0];

    // setInput("");
    // setSelectedFiles([]);
    // resetTranscript();

    try 
    {

      const formData = new FormData();

      formData.append('message', currInput);
      formData.append('user', userId);
      formData.append('project', projectId);
      formData.append('session_id', sessionId);
      
      
      if(currFile) 
      {
        const base64 = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result.split(",")[1]);
          reader.onerror = reject;
          reader.readAsDataURL(currFile);
        });

        formData.append("uploaded_image", base64);
	    }

      setLoading(true);

      try   
      {
        const res = await axios.post(
          `${URL}/chatbot/chat`,
          // {
          //   message: input,
          //   user: "test",
          //   project: "test",
          //   session_id: sessionId,
          // },
          formData,
          { 
            headers: 
              { "Content-Type": "application/json" } 
          }
        );
        const botMsg = { sender: "bot", content: res.data.response };
        setMessages((prev) => [...prev, botMsg]);
      } catch (err) {
        console.log(err);
      } finally {
        setLoading(false);
      }

    } catch (err) {
      console.error("Chat error", err);
      setMessages((prev) => [
        ...prev,
        { sender: "bot", content: "Oops! Something went wrong." },
      ]);
    }
  };




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
          className={`absolute bottom-0 h-[90svh] md:h-[95vh] left-1/2 w-full max-w-[420px] -translate-x-1/2 px-4 pt-4 pb-0 ${
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

          <div className="mx-auto max-w-[380px] rounded-t-3xl bg-white shadow-md flex flex-col h-full overflow-hidden">
            <ChatHeader onClose={onClose} dragHandleProps={{ onPointerDown: startDrag }} />

          <div 
            ref={messagesEndRef}
            className="flex-1 overflow-y-auto px-5 pt-1 pb-3 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
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

          <div className="flex-shrink-0 flex flex-col px-4 py-3 gap-2">
            <hr className="border-t border-gray-200/70" />
            <ChatInput onSend={handleSend} />
          </div>

          <div className="mt-auto grid grid-cols-2 gap-4 px-4 pb-4">
            <button 
              onClick={() => navigate("/home")}
              className="rounded-[8px] font-regular bg-[#D9D9D9] px-4 py-2 text-black-700">
              Previous
            </button>

            <button className="rounded-[8px] font-regular bg-[#D9D9D9] px-4 py-2 text-black-700">
              Next
            </button>

          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
