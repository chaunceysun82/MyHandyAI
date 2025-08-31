import React, { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import ChatWindow from "../components/Chat/ChatWindow";
import axios from "axios";
import { RotatingLines } from 'react-loader-spinner';
import MobileWrapper from "../components/MobileWrapper";

const Chat = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const URL = process.env.REACT_APP_BASE_URL;

  console.log("URL:", URL);

  const [loading, setLoading] = useState(true);

  const tips = [
    "💡 Tip: You can upload multiple files for better results.",
    "⚠️ Please be careful when using any tools or materials provided by MyHandyAI.",
    "📂 Keep your project organized for quick access.",
    "💬 Use short and clear prompts for better responses.",
  ];

  const [currentTipIndex, setCurrentTipIndex] = useState(0);
  
  useEffect(() => {
    if (loading) {
      const interval = setInterval(() => {
        setCurrentTipIndex((prevIndex) => (prevIndex + 1) % tips.length);
      }, 2500);
      return () => clearInterval(interval);
    }
  }, [loading, tips.length]);
  
  // const [statusCheck, setStatusCheck] = useState(false);

  const { projectId, projectName, userId, userName } = location.state || {};

  // Redirect if no projectId
  useEffect(() => {
    if (!projectId) {
      navigate("/", { replace: true });
    }
  }, [projectId, navigate]);


  useEffect(() => {
  const fetchStatus = async () => {
    let statusCheck = false;

    try {
      const response = await axios.get(`${URL}/generation/status/${projectId}`);

      if (response) 
      {
        const message = response.data.message;
        console.log("Message:", message);

        if (message === "generation completed") {
          statusCheck = true;
        }
      }
    } catch (err) {
      console.log("Err: ", err);
    } finally 
    {
      setTimeout(() => {
        setLoading(false);
        if(statusCheck)
        {
          navigate(`/projects/${projectId}/overview`, {state: {userId, userName}});
        }
      }, 800);
    }
  };

  fetchStatus();
}, [projectId, navigate]);



  const [open, setOpen] = useState(true);


  const handleClose = () => {
    setOpen(false);
    navigate("/home");
  };


  if (!projectId || !userId) return null;

  return (

    <MobileWrapper>

      {(loading) ? (
        <div className="flex flex-col items-center justify-center h-screen w-full px-4">
            <RotatingLines
              strokeColor="blue"
              strokeWidth="2"
              animationDuration="0.8"
              width="45"
              visible={true}
            />
            <p className="mt-6 text-gray-600 text-sm text-center transition-all duration-500 ease-in-out">
              {tips[currentTipIndex]}
            </p>
        </div>
      ) : (
        <ChatWindow
          isOpen={open}
          onClose={handleClose}
          projectId={projectId}
          projectName={projectName}
          userId={userId}
          userName={userName}
          URL={URL}
        />
      )}

    </MobileWrapper>
    
  );
};

export default Chat;
