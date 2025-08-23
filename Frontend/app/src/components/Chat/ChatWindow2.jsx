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
  stepNumber
}) {

//   console.log("User ID:", userId);
  console.log("Project ID:", projectId);
  console.log("Step Number:", stepNumber);

  const [render, setRender] = useState(isOpen);
  const [closing, setClosing] = useState(false);
  const [opening, setOpening] = useState(false);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(false);
  const [status2, setStatus2] = useState(false);

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


//   const api = secondChatStatus ? "step-guidance" : "chatbot";

//   const [bool, setBool] = useState(null);

//   useEffect(() => {
//     const check = async () => {
//       try 
//       {
//         const res = await axios.get(`${URL}/step-guidance/started/${projectId}`);
//         console.log("Bool:", res.data);
//         if (res.data) 
//         {
//           setBool(res.data);
//         }
//       } catch (err)
//       {
//         console.error("Error checking step guidance status:", err);
//       }
//     }
//     check();
//   }, []);



  const [drag, setDrag] = useState({ active: false, startY: 0, dy: 0 });
  const THRESHOLD = 120;
  const messagesEndRef = useRef(null);

//   const STORAGE_SESSION_KEY = `sessionId_${userId}_${projectId}`;
  const STORAGE_MESSAGES_KEY = `messages_${projectId}`;

  const navigate = useNavigate();
  
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem(STORAGE_MESSAGES_KEY);
    return saved ? JSON.parse(saved) : [];
  });

//   const [messages, setMessages] = useState([]);

 
//   const [sessionId, setSessionId] = useState(() => {
//     const saved = localStorage.getItem(STORAGE_SESSION_KEY);
//     return saved || null;
//   })
    const [sessionId, setSessionId] = useState(null);

    // useEffect(() => {
    //     const getSessionId = async () => {
    //         try {
    //             const res = await axios.get(`${URL}/step-guidance/session/${projectId}`);
    //             // console.log("Res", res.data.session);
    //             if(res.data)
    //             {
    //                 setSessionId(res.data.session_id);
    //             }
    //         } catch (err) {
    //             console.error("Error fetching session ID:", err);
    //         }
    //     }
    //     getSessionId();
    // }, []);
    // console.log("Session ID:", sessionId);


  // useEffect(() => {
  //   const getSessionId = async () => {
  //     try {
  //       const res = await axios.get(`${URL}/${api}/session/${projectId}`);
  //       // console.log("Res", res.data.session);
  //       if(res.data)
  //       {
  //         setSessionId(res.data.session);
  //       }
  //     } catch (err) {
  //       console.error("Error fetching session ID:", err);
  //     }
  //   }
  //   getSessionId();
  // }, []);



  useEffect(() => {
	if (messagesEndRef.current) 
	{
		messagesEndRef.current.scrollTo({
			top: messagesEndRef.current.scrollHeight,
			behavior: "smooth"
		});
	}
   }, [messages]);


  //  useEffect(() => {
  //     const firstRun = async () => {
  //         try {
  //           const historyRes = await axios.get(`${URL}/chatbot/session/${sessionId}/history`);
  //           const formattedMessages = historyRes.data.map(({role, message}) => ({
  //             sender: role === "user" ? "user" : "bot",
  //             content: message,
  //         }));
  //         setMessages(formattedMessages);
  //       } catch (err) {
  //         setMessages([{sender: "bot", content: "Failed to load chat history."}]);
  //       }
  //     } 
  //     if(secondChatStatus)
  //     {
  //       firstRun(); // this is only run if secondChatStatus is true
  //     }
  //  }, []);
  
  

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


  useEffect(() => {
      const getStatus = async () => {
        if(status === true)
        {
          // Goal is to call the generation api endpoint every 5 seconds until
          // the message doesn't say "genertion completed". Once that is done,
          // navigate to the project overview page/screen.
            try 
            {
              const response = await axios.post(`${URL}/generation/all/${projectId}`);

              if(response)
              {
                setStatus2(true);
              }
            } catch (err)
            {
              console.log("Err: ", err);
            }
          
        }
      }
      getStatus();
  }, [status, navigate]);



  useEffect(() => {
        if(status2 === true)
        {
          // Goal is to call the generation api endpoint every 5 seconds until
          // the message doesn't say "genertion completed". Once that is done,
          // navigate to the project overview page/screen.
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
                    // Reset the session ID
                    navigate(`/projects/${projectId}/overview`);
                  }
                }
              } 
              catch (err)
              {
                console.log("Err: ", err);
              }
            }, 5000);

            return () => clearInterval(interval);
        }
  }, [status2, navigate]);



  
  // Persist messages locally
    useEffect(() => {
        localStorage.setItem(STORAGE_MESSAGES_KEY, JSON.stringify(messages));
    }, [messages, STORAGE_MESSAGES_KEY]);



  // Load or start session
//   useEffect(() => {
//     // console.log("Session ID:", sessionId);
//     let cancelled = false;
//     async function loadOrStartSession() {
//     //   console.log("Loading or starting session for:", { projectId, userId });
//       if(cancelled) return;

//       if(!sessionId)
//       {
//         try {
//             // console.log("Full URL", `${URL}/step-guidance/start`);

//             const res = await axios.post(
//               `${URL}/step-guidance/start`,
//               { project: projectId },
//               { headers: { "Content-Type": "application/json" } 
//             });
//             if(!cancelled)
//             {
//                 console.log("Response from starting session:", res.data);
//                 setSessionId(res.data.session_id);
//                 // localStorage.setItem(STORAGE_SESSION_KEY, res.data.session_id);
//                 setMessages([{ sender: "bot", content: res.data.response }]);
//             }
            
//             // if(secondChatStatus)
//             // {
//             //   setBool(false);
//             // }

//         } catch (err) 
//         {
//           console.error("Intro message error", err);
//         }
//       } else {
//         try {
//           const historyRes = await axios.get(`${URL}/chatbot/session/${sessionId}/history`);
//           if(!cancelled)
//           {
//             const formattedMessages = historyRes.data.map(({role, message}) => ({
//                 sender: role === "user" ? "user" : "bot",
//                 content: message,
//             }));

//             console.log("Formatted Messages:", formattedMessages);
//             setMessages(formattedMessages);
//           }
//         } catch (err) {
//             if(!cancelled)
//             {
//                 setMessages([{sender: "bot", content: "Failed to load chat history."}]);
//             }
//         }
//       }
//     }
//     loadOrStartSession();

//     return () => { cancelled = true; };
//   }, [projectId]);

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
                    // No session exists, start new one
                    const startRes = await axios.post(
                        `${URL}/step-guidance/start`,
                        { project: projectId },
                        { headers: { "Content-Type": "application/json" }}
                    );
                    
                    if (!cancelled) {
                        console.log("Response from starting session:", startRes.data);
                        setSessionId(startRes.data.session);
                        setMessages([{ sender: "bot", content: startRes.data.response }]);
                    }
                }
            } catch (err) {
                console.log("Error during session initialization:", err);
                // if (!cancelled) {
                //     console.error("Session initialization error:", err);
                //     // Start new session as fallback
                //     try {
                //         const startRes = await axios.post(
                //             `${URL}/step-guidance/start`,
                //             { project: projectId },
                //             { headers: { "Content-Type": "application/json" }}
                //         );
                        
                //         if (!cancelled) {
                //             setSessionId(startRes.data.session_id);
                //             setMessages([{ sender: "bot", content: startRes.data.response }]);
                //         }
                //     } catch (startErr) {
                //         console.error("Failed to start new session:", startErr);
                //     }
                // }
            }
        };
        
        initializeSession();
        
        return () => {
            cancelled = true;
        };
    }, [projectId, URL]); // Remove the separate sessionId fetching useEffect


  // Send message handler
const handleSend = async (text, files = []) => {
    if (!text.trim() && files.length === 0) return;


    let messageContent = text.trim();
    
    try
    {
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

      // Prepare payload for backend (combine text and first image)
      const currInput = text;
      let uploadedimage = null;

      const currFile = files[0];
      if(currFile && currFile.type.startsWith('image/')) {
        uploadedimage = await toBase64(currFile);
      }

      const payload = 
      {
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

      // check for the current_state of the response:
      console.log("Current State:", res.data.current_state);

      if(res.data.current_state === 'complete')
      {
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

          {status === false ? (
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
              )
          }
          

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
