import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { MessageCircle, Users, Zap, Copy, Check } from "lucide-react";

const Index = () => {
  const [roomId, setRoomId] = useState("");
  const [copied, setCopied] = useState(false);

  const generateRoomId = () => {
    const id = Math.random().toString(36).substring(2, 15);
    setRoomId(id);
  };

  const joinChat = () => {
    if (roomId.trim()) {
      window.location.href = `/chat/${roomId.trim()}`;
    }
  };

  const copyRoomLink = async () => {
    const link = `${window.location.origin}/chat/${roomId}`;
    await navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-chat-background">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center mb-16">
          <div className="flex justify-center mb-6">
            <div className="p-4 bg-primary rounded-full">
              <MessageCircle className="h-8 w-8 text-primary-foreground" />
            </div>
          </div>
          <h1 className="text-4xl font-bold mb-4">Real-time Chat</h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Connect instantly with anyone using a shareable chat room link. 
            Simple, fast, and secure messaging.
          </p>
        </div>

        <div className="max-w-md mx-auto mb-16">
          <Card>
            <CardHeader>
              <CardTitle>Start Chatting</CardTitle>
              <CardDescription>
                Create a new room or join an existing one
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Input
                  placeholder="Enter room ID"
                  value={roomId}
                  onChange={(e) => setRoomId(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && joinChat()}
                />
                <div className="flex gap-2">
                  <Button onClick={generateRoomId} variant="outline" className="flex-1">
                    Generate Room
                  </Button>
                  <Button onClick={joinChat} disabled={!roomId.trim()} className="flex-1">
                    Join Chat
                  </Button>
                </div>
                
                {roomId && (
                  <div className="mt-4 p-3 bg-muted rounded-lg">
                    <p className="text-sm text-muted-foreground mb-2">Share this link with others:</p>
                    <div className="flex gap-2">
                      <Input 
                        value={`${window.location.origin}/chat/${roomId}`} 
                        readOnly 
                        className="text-sm"
                      />
                      <Button 
                        onClick={copyRoomLink} 
                        variant="outline" 
                        size="sm"
                        className="shrink-0"
                      >
                        {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Zap className="h-5 w-5 text-primary" />
                </div>
                <h3 className="font-semibold">Real-time</h3>
              </div>
              <p className="text-sm text-muted-foreground">
                Messages are delivered instantly with WebSocket technology
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Users className="h-5 w-5 text-primary" />
                </div>
                <h3 className="font-semibold">Easy Sharing</h3>
              </div>
              <p className="text-sm text-muted-foreground">
                Share room links to start chatting with anyone instantly
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <MessageCircle className="h-5 w-5 text-primary" />
                </div>
                <h3 className="font-semibold">Simple UI</h3>
              </div>
              <p className="text-sm text-muted-foreground">
                Clean, modern interface with typing indicators and status
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Index;
