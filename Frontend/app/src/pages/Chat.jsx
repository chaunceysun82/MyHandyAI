import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import { MoonIcon, SunIcon } from "@heroicons/react/24/solid";
import {ReactComponent as Microphone} from '../assets/recorder-microphone.svg';
import {ReactComponent as File} from '../assets/file-upload.svg';
import SpeechRecognition, {useSpeechRecognition} from 'react-speech-recognition';
import { useLocation, useNavigate } from "react-router-dom";

const Chat = () => {

  const location = useLocation();
  const navigate = useNavigate();
  const { projectId, projectName, userId } = location.state || {};

  if(!projectId)
  {
    navigate("/", {replace: true});
  }
  const user = userId;
  
  // Call the /session/startchat endpoint:
  useEffect(() => {
    const fetchSession = async () => {
        try {
          const res = await axios.get(`${URL}/session`, 
          {
            user: userId,
            project: projectId
          },
          { 
            headers: { "Content-Type": "application/json" } 
          })
          localStorage.setItem("session", res.data.session);
        } catch (errr) {
          alert("Could not fetch the session ID successfully.");
        }
      }
      fetchSession();
  }, []);

  const STORAGE_SESSION_KEY = localStorage.getItem("session");
  const STORAGE_MESSAGES_KEY = `messages_${user}_${projectId}`;


  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem(STORAGE_MESSAGES_KEY);
    return saved ? JSON.parse(saved) : [];
  });

  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState(localStorage.getItem(STORAGE_SESSION_KEY) || "");
  const [selectedFiles, setSelectedFiles] = useState([]);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const [theme, setTheme] = useState("light");

  const URL = process.env.REACT_APP_BASE_URL;

  const {transcript, listening, resetTranscript, browserSupportsSpeechRecognition} = useSpeechRecognition();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({behavior: 'smooth'})
  }, [messages]);


  useEffect(() => {
    if(transcript)
    {
      setInput(transcript);
    }
  }, [transcript]);


  const handleMicrophone = () => {
    if(!browserSupportsSpeechRecognition)
    {
      alert("Browser does not support speech recognition.");
      return;
    }
    if(listening)
    {
      SpeechRecognition.stopListening();
    }else{
      resetTranscript();
      SpeechRecognition.startListening({
        continuous: false,
        language: 'en-US'
      });
    }
  };

  const fileHandle = () => 
  {
    fileInputRef.current?.click();
  }

  const removeFile = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  }

  const fileHandleSelect = (event) => {
    const files = Array.from(event.target.files);
    setSelectedFiles(prev => [...prev, ...files]);
    event.target.value = ''
  }



  useEffect(() => {
    localStorage.setItem(STORAGE_MESSAGES_KEY, JSON.stringify(messages));
  }, [messages, STORAGE_MESSAGES_KEY]);

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

  const handleSend = async () => {
    if (!input.trim() && selectedFiles.length === 0) return;


    let messageContent = input.trim();
    
    if (selectedFiles.length > 0) 
    {
      const fileNames = selectedFiles.map(f => f.name).join(', ');
      if (messageContent) {
        messageContent = `${messageContent}\n\nFiles: ${fileNames}`;
      } 
      else 
      {
        messageContent = `Files: ${fileNames}`;
      }
    }


    const userMsg = { 
      sender: "user", 
      content: messageContent,
      // files: selectedFiles.length > 0 ? selectedFiles.map(f => f.name) : undefined 
    };

    setMessages((prev) => [...prev, userMsg]);

    const currInput = input;
    const currFiles = selectedFiles;

    setInput("");
    setSelectedFiles([]);
    resetTranscript();

    try 
    {

      const formData = new FormData();

      formData.append('message', currInput);
      formData.append('user', 'test');
      formData.append('project', 'test');
      formData.append('session_id', sessionId);
      
      
      currFiles.forEach((file, index) => {
        formData.append(`file_${index}`, file);
      });

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
      console.error("Chat error", err);
      setMessages((prev) => [
        ...prev,
        { sender: "bot", content: "Oops! Something went wrong." },
      ]);
    }
  };


  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleSend();
  };


  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  return (
    <div
      className={`relative flex flex-col h-screen max-w-md mx-auto p-4 border rounded-md shadow-md
        ${theme === "dark" ? "bg-gray-900 text-white border-gray-700" : "bg-white text-gray-900 border-gray-300"}
      `}
    >

      <input
        type="file"
        ref={fileInputRef}
        onChange={fileHandleSelect}
        multiple
        style={{ display: 'none' }}
        accept="*/*"
      />

      
      {/* Theme toggle button top right */}
      <h1 className="text-center text-xl font-semibold">
        {projectName || "Untitled Project"}
      </h1>

      <div className="absolute top-4 right-4 z-20">
        <label className="flex items-center cursor-pointer select-none">
          <input
            type="checkbox"
            onChange={toggleTheme}
            checked={theme === "dark"}
            className="sr-only"
          />
          <div
            className={`w-12 h-6 rounded-full p-1 flex items-center transition-all duration-300 relative ${
              theme === "dark" ? "bg-gray-700" : "bg-gray-300"
            }`}
          >
            <div
              className={`w-4 h-4 rounded-full flex items-center justify-center shadow-md transform transition-transform duration-300 ${
                theme === "dark" ? "translate-x-6 bg-gray-800 text-white" : "translate-x-0 bg-white text-yellow-400"
              }`}
            >
              {theme === "light" ? (
                <SunIcon className="w-3 h-3 text-yellow-400" />
              ) : (
                <MoonIcon className="w-3 h-3 text-white" />
              )}
            </div>
          </div>
        </label>
      </div>

      {/* Messages container */}
      <div
        className={`flex-1 mt-10 overflow-y-auto space-y-4 mb-4
          ${theme === "dark" ? "bg-gray-800" : "bg-gray-100"}
          p-4 rounded-lg
        `}
      >
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`px-4 py-2 rounded-lg max-w-xs break-words ${
                msg.sender === "user"
                  ? theme === "dark"
                    ? "bg-blue-700 text-white"
                    : "bg-blue-600 text-white"
                  : theme === "dark"
                  ? "bg-gray-600 text-white"
                  : "bg-gray-200 text-gray-900"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {selectedFiles.length > 0 && (
        <div className={`mb-4 p-2 rounded-lg ${theme === "dark" ? "bg-gray-800" : "bg-gray-100"}`}>
          <div className="text-sm font-medium mb-1">Selected Files:</div>
          <div className="space-y-1">
            {selectedFiles.map((file, index) => (
              <div key={index} className="flex items-center justify-between text-xs">
                <span className="truncate">
                  {file.name}
                </span>
                <button
                  onClick={() => removeFile(index)}
                  className={`ml-2 mr-2 font-bold text-blue-500 ${theme === 'dark' ? "hover:text-white" : "hover:text-black"}`}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input & send button */}
      <div className="flex items-center space-x-2">
        <div className="relative flex w-full items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              className={`flex-1 px-4 py-2 pr-20 rounded-lg border focus:outline-none
                ${
                  theme === "dark"
                    ? "bg-gray-700 border-gray-600 text-white placeholder-gray-300"
                    : "bg-white border-gray-300 text-gray-900 placeholder-gray-500"
                }
              `}
            />

            <div className="absolute right-2 flex items-center space-x-2">
              <button onClick={handleMicrophone} className={`p-1 rounded transition-all duration-300 ${
                listening ? 'bg-white text-white animate-pulse' : 'hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
              >
                <Microphone width={18} height={18} />
              </button>

              <button 
                className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-all duration-300"
                onClick={fileHandle}
              >
                <File width={18} height={18} />
              </button>
            </div>

        </div>
        
        <button
          onClick={handleSend}
          disabled={!input.trim() && selectedFiles.length === 0}
          className={`px-4 py-2 rounded-lg font-semibold
            ${(!input.trim() && selectedFiles.length === 0)
              ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
              : theme === "dark"
                ? "bg-blue-700 hover:bg-blue-600 text-white"
                : "bg-blue-600 hover:bg-blue-700 text-white"
            }
          `}
        >
          Send
        </button>
      </div>
      

    </div>
  );
};

export default Chat;