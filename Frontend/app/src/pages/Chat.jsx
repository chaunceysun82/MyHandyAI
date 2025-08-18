import React, { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import ChatWindow from "../components/Chat/ChatWindow";
import axios from "axios";

const Chat = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const URL = process.env.REACT_APP_BASE_URL;

  const { projectId, projectName, userId } = location.state || {};

  // Redirect if no projectId
  useEffect(() => {
    if (!projectId) {
      navigate("/", { replace: true });
    }
  }, [projectId, navigate]);


  useEffect(() => {
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
  }, []);



  const [open, setOpen] = useState(true);


  const handleClose = () => {
    setOpen(false);
    navigate("/home");
  };


  if (!projectId || !userId) return null;

  return (
    <ChatWindow
      isOpen={open}
      onClose={handleClose}
      projectId={projectId}
      projectName={projectName}
      userId={userId}
      URL={URL}
    />
  );
};

export default Chat;
