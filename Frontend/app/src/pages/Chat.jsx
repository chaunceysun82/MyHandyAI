import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import { MoonIcon, SunIcon } from "@heroicons/react/24/solid";

const Chat = ({ projectId = "default" }) => {
  const STORAGE_KEY = `chatMessages`;
  const INTRO_SHOWN_KEY = "introShown";

  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : [];
  });

  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState("");
  const messagesEndRef = useRef(null);

  const [theme, setTheme] = useState("light");

  const URL = process.env.REACT_APP_BASE_URL;

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    const introShown = localStorage.getItem(INTRO_SHOWN_KEY);
    if (introShown) return;

    const sendIntro = async () => {
      try {
        const res = await axios.post(
          `${URL}/chatbot/start`,
          { user: "test", project: "test" },
          { headers: { "Content-Type": "application/json" } }
        );

        setMessages([{ sender: "bot", content: res.data.intro_message }]);
        setSessionId(res.data.session_id);

        localStorage.setItem(INTRO_SHOWN_KEY, "true");
      } catch (err) {
        console.error("Intro message error", err);
      }
    };

    sendIntro();
  }, [projectId]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg = { sender: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    try {
      const res = await axios.post(
        `${URL}/chatbot/chat`,
        {
          message: input,
          user: "test",
          project: "test",
          session_id: sessionId,
        },
        { headers: { "Content-Type": "application/json" } }
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
      {/* Theme toggle button top right */}
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

      {/* Input & send button */}
      <div className="flex items-center space-x-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          className={`flex-1 px-4 py-2 rounded-lg border focus:outline-none
            ${
              theme === "dark"
                ? "bg-gray-700 border-gray-600 text-white placeholder-gray-300"
                : "bg-white border-gray-300 text-gray-900 placeholder-gray-500"
            }
          `}
        />
        <button
          onClick={handleSend}
          className={`px-4 py-2 rounded-lg font-semibold
            ${
              theme === "dark"
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
