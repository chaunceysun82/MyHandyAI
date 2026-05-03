import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const Chat = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { projectId, projectName } = location.state || {};

  useEffect(() => {
    navigate("/home", {
      replace: true,
      state: projectId
        ? {
            openChatProject: {
              projectId,
              projectName,
            },
          }
        : null,
    });
  }, [navigate, projectId, projectName]);

  return null;
};

export default Chat;
