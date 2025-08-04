import { useEffect, useRef, useState } from "react";
import { MessageBubble, Message } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import { InputBar } from "./InputBar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Wifi, WifiOff } from "lucide-react";

interface ChatWindowProps {
  roomId: string;
  currentUser: string;
  otherUser: string;
}

export const ChatWindow = ({ roomId, currentUser, otherUser }: ChatWindowProps) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isOtherUserTyping, setIsOtherUserTyping] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout>();

  // Placeholder function for future AI translation
  const translateMessage = async (message: string, targetLang: string): Promise<string> => {
    // TODO: Implement AI translation
    return message;
  };

  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  };

  useEffect(() => {
    // Connect to WebSocket
    const wsUrl = `ws://localhost:8000/ws/chat/${roomId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('Connected to chat room:', roomId);
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'typing') {
          if (data.from !== currentUser) {
            setIsOtherUserTyping(data.isTyping);
          }
        } else if (data.type === 'message') {
          const message: Message = {
            from: data.from,
            to: data.to,
            text: data.text,
            lang: data.lang || 'en',
            timestamp: data.timestamp,
            status: 'sent'
          };
          
          setMessages(prev => prev.map(msg => 
            msg.timestamp === message.timestamp && msg.from === currentUser 
              ? { ...msg, status: 'sent' as const }
              : msg
          ).concat(message.from !== currentUser ? [message] : []));
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    ws.onclose = () => {
      console.log('Disconnected from chat room');
      setIsConnected(false);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };

    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
      ws.close();
    };
  }, [roomId, currentUser]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isOtherUserTyping]);

  const sendMessage = (text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket is not connected');
      return;
    }

    const message: Message = {
      from: currentUser,
      to: otherUser,
      text,
      lang: 'en',
      timestamp: new Date().toISOString(),
      status: 'sending'
    };

    // Add message with sending status
    setMessages(prev => [...prev, message]);

    // Send to WebSocket
    wsRef.current.send(JSON.stringify({
      type: 'message',
      ...message
    }));

    // Update status to sent (optimistic update)
    setTimeout(() => {
      setMessages(prev => prev.map(msg => 
        msg.timestamp === message.timestamp && msg.from === currentUser
          ? { ...msg, status: 'sent' as const }
          : msg
      ));
    }, 500);
  };

  const handleTyping = (typing: boolean) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    setIsTyping(typing);
    
    wsRef.current.send(JSON.stringify({
      type: 'typing',
      from: currentUser,
      to: otherUser,
      isTyping: typing
    }));

    // Clear typing after 3 seconds of inactivity
    if (typing) {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
      typingTimeoutRef.current = setTimeout(() => {
        handleTyping(false);
      }, 3000);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-chat-background">
      {/* Header */}
      <div className="flex items-center justify-between p-4 bg-chat-sidebar border-b">
        <div>
          <h1 className="text-lg font-semibold">{otherUser}</h1>
          <p className="text-sm text-muted-foreground">Room: {roomId}</p>
        </div>
        <Badge variant={isConnected ? "default" : "destructive"} className="gap-1">
          {isConnected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
          {isConnected ? "Connected" : "Disconnected"}
        </Badge>
      </div>

      {/* Messages */}
      <ScrollArea ref={scrollAreaRef} className="flex-1 p-4">
        <div className="space-y-1">
          {messages.map((message, index) => {
            const showTimestamp = index === 0 || 
              new Date(messages[index - 1]?.timestamp).getTime() < new Date(message.timestamp).getTime() - 300000; // 5 minutes
            
            return (
              <MessageBubble
                key={`${message.timestamp}-${message.from}`}
                message={message}
                isCurrentUser={message.from === currentUser}
                showTimestamp={showTimestamp}
              />
            );
          })}
          
          <TypingIndicator 
            userName={otherUser} 
            isVisible={isOtherUserTyping}
          />
        </div>
      </ScrollArea>

      {/* Input */}
      <InputBar
        onSendMessage={sendMessage}
        onTyping={handleTyping}
        disabled={!isConnected}
      />
    </div>
  );
};