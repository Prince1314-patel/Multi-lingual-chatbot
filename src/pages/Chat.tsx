import { useParams } from "react-router-dom";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { Button } from "@/components/ui/button";
import { useState, useEffect } from "react";

const Chat = () => {
  const { roomId } = useParams<{ roomId: string }>();
  const [currentUser, setCurrentUser] = useState("");

  useEffect(() => {
    // Generate a unique user ID for this session
    const userId = `user-${Math.random().toString(36).substring(2, 9)}`;
    setCurrentUser(userId);
  }, []);
  
  if (!roomId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">Invalid Chat Room</h1>
          <p className="text-muted-foreground mb-4">No room ID provided in the URL.</p>
          <Button onClick={() => window.location.href = '/'}>
            Go Home
          </Button>
        </div>
      </div>
    );
  }

  if (!currentUser) {
    return <div>Loading...</div>;
  }

  return (
    <div className="h-screen">
      <ChatWindow
        roomId={roomId}
        currentUser={currentUser}
        otherUser="other-users"
      />
    </div>
  );
};

export default Chat;