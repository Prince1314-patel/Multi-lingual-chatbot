import { useParams, useSearchParams } from "react-router-dom";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { Button } from "@/components/ui/button";
import { useState } from "react";

const Chat = () => {
  const { roomId } = useParams<{ roomId: string }>();
  const [searchParams] = useSearchParams();
  const [currentUser, setCurrentUser] = useState(searchParams.get('user') || 'userA');
  
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

  const otherUser = currentUser === 'userA' ? 'userB' : 'userA';

  return (
    <div className="h-screen">
      {/* User toggle for testing */}
      <div className="absolute top-4 left-4 z-10 bg-background border rounded-lg p-2 shadow-lg">
        <div className="flex gap-2">
          <Button
            variant={currentUser === 'userA' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setCurrentUser('userA')}
          >
            User A
          </Button>
          <Button
            variant={currentUser === 'userB' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setCurrentUser('userB')}
          >
            User B
          </Button>
        </div>
      </div>

      <ChatWindow
        roomId={roomId}
        currentUser={currentUser}
        otherUser={otherUser}
      />
    </div>
  );
};

export default Chat;