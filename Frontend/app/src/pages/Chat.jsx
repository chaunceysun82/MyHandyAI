import React, { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import ChatWindow from "../components/Chat/ChatWindow";

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
