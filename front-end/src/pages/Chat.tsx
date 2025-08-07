import { useParams, useNavigate } from "react-router-dom";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { UserOnboarding } from "@/components/onboarding/UserOnboarding";
import { Button } from "@/components/ui/button";
import { useState, useEffect } from "react";
import { UserPreferences, hasValidPreferences, loadUserPreferences } from "@/lib/userPreferences";

const Chat = () => {
  const { roomId } = useParams<{ roomId: string }>();
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState("");
  const [userPreferences, setUserPreferences] = useState<UserPreferences | null>(null);
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    if (!roomId) return;

    // Check if user has valid preferences for this room
    if (hasValidPreferences(roomId)) {
      const preferences = loadUserPreferences(roomId);
      setUserPreferences(preferences);
      setShowOnboarding(false);
    } else {
      // Show onboarding if no valid preferences found
      setShowOnboarding(true);
    }

    // Generate a unique user ID for this session
    const userId = `user-${Math.random().toString(36).substring(2, 9)}`;
    setCurrentUser(userId);
  }, [roomId]);

  const handleOnboardingComplete = (preferences: UserPreferences) => {
    setUserPreferences(preferences);
    setShowOnboarding(false);
  };

  const handleOnboardingBack = () => {
    navigate('/');
  };
  
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

  // Show onboarding if needed
  if (showOnboarding) {
    return (
      <UserOnboarding
        roomId={roomId}
        onComplete={handleOnboardingComplete}
        onBack={handleOnboardingBack}
      />
    );
  }

  // Show loading while preferences are being loaded
  if (!currentUser || !userPreferences) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading chat...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen">
      <ChatWindow
        roomId={roomId}
        currentUser={currentUser}
        userPreferences={userPreferences}
        otherUser="other-users"
      />
    </div>
  );
};

export default Chat;