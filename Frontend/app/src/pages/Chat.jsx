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

  const [loading, setLoading] = useState(true);
  
  
  // const [statusCheck, setStatusCheck] = useState(false);

  const { projectId, projectName, userId } = location.state || {};

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

      if (response) {
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
          navigate(`/projects/${projectId}/overview`, {
            state: {
              projectId,
              projectName: projectName || "Project"
            }
          });
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
        <div className="flex items-center justify-center h-screen">
            <RotatingLines
              strokeColor="blue"
              strokeWidth="2"
              animationDuration="0.8"
              width="45"
              visible={true}
            />
        </div>
      ) : (
        <ChatWindow
          isOpen={open}
          onClose={handleClose}
          projectId={projectId}
          projectName={projectName}
          userId={userId}
          URL={URL}
        />
      )}

    </MobileWrapper>
    
  );
};

export default Chat;
