import MessageBubble from "./MessageBubble";

export default function MessageList({ messages = [] }) {
  return (
    <div>
      {messages.map((m, index) => {
        let content = m.content || "";
        if (m.files && m.files.length > 0) {
          const fileText = `\nFiles:\n${m.files.join("\n")}`;
          content += fileText;
        }

        return (
          <MessageBubble key={index} role={m.sender}>
            {content}
          </MessageBubble>
        );
      })}
    </div>
  );
}
