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
  const [showChatWindow, setShowChatWindow] = useState(false);
  const [generationInProgress, setGenerationInProgress] = useState(false);

  const tips = [
    "💡 We are now analyzing your project...",
    "💡 Putting  your tailored repair recipe together...this may take a couple of minutes...",
    "💡 Almost there, hang tight! MyHandyAI is gathering the best tools for you...",
    "💡 Thanks for your patience! Almost done..."
  ];

  const [currentTipIndex, setCurrentTipIndex] = useState(0);
  
  useEffect(() => {
    if (loading || generationInProgress) {
      const interval = setInterval(() => {
        setCurrentTipIndex((prevIndex) => (prevIndex + 1) % tips.length);
      }, 2500);
      return () => clearInterval(interval);
    }
  }, [loading, generationInProgress, tips.length]);
  
  // const [statusCheck, setStatusCheck] = useState(false);

  const { projectId, projectName, userId, userName } = location.state || {};

  // Redirect if no projectId
  useEffect(() => {
    if (!projectId) {
      navigate("/", { replace: true });
    }
  }, [projectId, navigate]);

  // Poll generation status when in progress
  useEffect(() => {
    if (!generationInProgress || !projectId) return;

    const pollGenerationStatus = async () => {
      try {
        const generationRes = await axios.get(`${URL}/generation/status/${projectId}`);
        const generationMessage = generationRes.data?.message;
        
        if (generationMessage === "generation completed") {
          // Generation completed - redirect to overview
          setGenerationInProgress(false);
          navigate(`/projects/${projectId}/overview`, {state: {userId, userName}});
        }
        // If still in progress, continue polling
      } catch (err) {
        console.log("Error polling generation status:", err);
      }
    };

    const interval = setInterval(pollGenerationStatus, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, [generationInProgress, projectId, navigate, URL, userId, userName]);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        // Check conversation status first
        const conversationRes = await axios.get(`${URL}/api/v1/information-gathering-agent/thread/${projectId}`);
        const conversationStatus = conversationRes.data?.conversation_status;
        
        console.log("Chat: Conversation status:", conversationStatus);
        
        // If conversation is COMPLETED, check generation status
        if (conversationStatus === "COMPLETED") {
          try {
            const generationRes = await axios.get(`${URL}/generation/status/${projectId}`);
            const generationMessage = generationRes.data?.message;
            console.log("Chat: Generation status:", generationMessage);
            
            if (generationMessage === "generation completed") {
              // Both completed - go to overview
              setLoading(false);
              navigate(`/projects/${projectId}/overview`, {state: {userId, userName}});
            } else if (generationMessage === "generation in progress") {
              // Conversation done, generation in progress - show loading and poll
              setGenerationInProgress(true);
              setLoading(false); // Stop initial loading, but keep showing tips
            } else {
              // Conversation completed but generation not started - redirect to overview
              setLoading(false);
              navigate(`/projects/${projectId}/overview`, {state: {userId, userName}});
            }
          } catch (genErr) {
            console.log("Error checking generation status:", genErr);
            // If generation check fails but conversation is completed, go to overview
            setLoading(false);
            navigate(`/projects/${projectId}/overview`, {state: {userId, userName}});
          }
        } else {
          // Conversation not completed - show chat window
          setLoading(false);
          setShowChatWindow(true);
        }
      } catch (convErr) {
        console.log("Error checking conversation status:", convErr);
        // If conversation check fails, check generation status as fallback
        try {
          const generationRes = await axios.get(`${URL}/generation/status/${projectId}`);
          const generationMessage = generationRes.data?.message;
          
          if (generationMessage === "generation completed") {
            setLoading(false);
            navigate(`/projects/${projectId}/overview`, {state: {userId, userName}});
          } else {
            // Show chat as fallback
            setLoading(false);
            setShowChatWindow(true);
          }
        } catch (genErr) {
          console.log("Error checking generation status:", genErr);
          // Default to showing chat
          setLoading(false);
          setShowChatWindow(true);
        }
      }
    };

    if (projectId) {
      fetchStatus();
    }
  }, [projectId, navigate, URL, userId, userName]);



  const [open, setOpen] = useState(true);


  const handleClose = () => {
    setOpen(false);
    navigate("/home");
  };


  if (!projectId || !userId) return null;

  return (

    <MobileWrapper>

      {(loading || generationInProgress) ? (
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
      ) : showChatWindow ? (
        <ChatWindow
          isOpen={open}
          onClose={handleClose}
          projectId={projectId}
          projectName={projectName}
          userId={userId}
          userName={userName}
          URL={URL}
        />
      ) : null}

    </MobileWrapper>
    
  );
};

export default Chat;
