import React, { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import ChatWindow from "../components/Chat/ChatWindow";
import axios from "axios";
import { RotatingLines } from 'react-loader-spinner';

const Chat = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const URL = process.env.REACT_APP_BASE_URL;

  const [loading, setLoading] = useState(false);

  const { projectId, projectName, userId } = location.state || {};

  // Redirect if no projectId
  useEffect(() => {
    if (!projectId) {
      navigate("/", { replace: true });
    }
  }, [projectId, navigate]);


  useEffect(() => {
  const fetchStatus = async () => {
    try {
      setLoading(true);

      const response = await axios.get(`${URL}/generation/status/${projectId}`);

      if (response) {
        const message = response.data.message;
        console.log("Message:", message);
        setLoading(false);

        if (message === "generation completed") {
          navigate(`/projects/${projectId}/overview`);
        }
      }
    } catch (err) {
      console.log("Err: ", err);
      setLoading(false);
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

    <div>

      {loading ? (
        <div className="items center justify-center flex flex-1 ">
            <RotatingLines
              strokeColor="blue"
              strokeWidth="2"
              animationDuration="0.1"
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

    </div>
    
  );
};

export default Chat;
