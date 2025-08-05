import { render, screen, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { ChatWindow } from '../ChatWindow';

// Mock the useWebSocket hook
const mockSendMessage = vi.fn();
const mockReconnect = vi.fn();

vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: vi.fn(() => ({
    isConnected: true,
    isConnecting: false,
    error: null,
    sendMessage: mockSendMessage,
    reconnect: mockReconnect
  }))
}));

// Mock the child components
vi.mock('../MessageBubble', () => ({
  MessageBubble: ({ message }: any) => (
    <div data-testid="message-bubble">
      {'type' in message && message.type === 'system' 
        ? message.content 
        : message.text}
    </div>
  )
}));

vi.mock('../TypingIndicator', () => ({
  TypingIndicator: ({ isVisible }: any) => 
    isVisible ? <div data-testid="typing-indicator">Typing...</div> : null
}));

vi.mock('../InputBar', () => ({
  InputBar: ({ onSendMessage, onTyping, disabled }: any) => (
    <div data-testid="input-bar">
      <button 
        onClick={() => onSendMessage('test message')}
        disabled={disabled}
      >
        Send
      </button>
    </div>
  )
}));

describe('ChatWindow User Notifications', () => {
  const defaultProps = {
    roomId: 'test-room',
    currentUser: 'user1',
    otherUser: 'user2'
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should display initial user count correctly', () => {
    render(<ChatWindow {...defaultProps} />);
    
    // Should show 1 user online (current user)
    expect(screen.getByText(/1 user online/)).toBeInTheDocument();
  });

  it('should handle user join notifications', async () => {
    const { useWebSocket } = await import('@/hooks/useWebSocket');
    const mockUseWebSocket = vi.mocked(useWebSocket);
    
    // Mock the onMessage callback to simulate user join
    let onMessageCallback: ((message: any) => void) | undefined;
    
    mockUseWebSocket.mockImplementation((roomId, options) => {
      onMessageCallback = options?.onMessage;
      return {
        isConnected: true,
        isConnecting: false,
        error: null,
        sendMessage: mockSendMessage,
        reconnect: mockReconnect
      };
    });

    render(<ChatWindow {...defaultProps} />);

    // Simulate user join message
    if (onMessageCallback) {
      onMessageCallback({
        type: 'user_join',
        user_id: 'user3',
        room_id: 'test-room',
        timestamp: new Date().toISOString()
      });
    }

    await waitFor(() => {
      // Should show 2 users online now
      expect(screen.getByText(/2 users online/)).toBeInTheDocument();
      // Should show join notification
      expect(screen.getByText('user3 joined the chat')).toBeInTheDocument();
    });
  });

  it('should handle user leave notifications', async () => {
    const { useWebSocket } = await import('@/hooks/useWebSocket');
    const mockUseWebSocket = vi.mocked(useWebSocket);
    
    let onMessageCallback: ((message: any) => void) | undefined;
    
    mockUseWebSocket.mockImplementation((roomId, options) => {
      onMessageCallback = options?.onMessage;
      return {
        isConnected: true,
        isConnecting: false,
        error: null,
        sendMessage: mockSendMessage,
        reconnect: mockReconnect
      };
    });

    render(<ChatWindow {...defaultProps} />);

    // First, simulate a user joining
    if (onMessageCallback) {
      onMessageCallback({
        type: 'user_join',
        user_id: 'user3',
        room_id: 'test-room',
        timestamp: new Date().toISOString()
      });
    }

    await waitFor(() => {
      expect(screen.getByText(/2 users online/)).toBeInTheDocument();
    });

    // Then simulate the same user leaving
    if (onMessageCallback) {
      onMessageCallback({
        type: 'user_leave',
        user_id: 'user3',
        room_id: 'test-room',
        timestamp: new Date().toISOString()
      });
    }

    await waitFor(() => {
      // Should be back to 1 user online
      expect(screen.getByText(/1 user online/)).toBeInTheDocument();
      // Should show leave notification
      expect(screen.getByText('user3 left the chat')).toBeInTheDocument();
    });
  });

  it('should not show notifications for current user join/leave', async () => {
    const { useWebSocket } = await import('@/hooks/useWebSocket');
    const mockUseWebSocket = vi.mocked(useWebSocket);
    
    let onMessageCallback: ((message: any) => void) | undefined;
    
    mockUseWebSocket.mockImplementation((roomId, options) => {
      onMessageCallback = options?.onMessage;
      return {
        isConnected: true,
        isConnecting: false,
        error: null,
        sendMessage: mockSendMessage,
        reconnect: mockReconnect
      };
    });

    render(<ChatWindow {...defaultProps} />);

    // Simulate current user join message (shouldn't show notification)
    if (onMessageCallback) {
      onMessageCallback({
        type: 'user_join',
        user_id: 'user1', // current user
        room_id: 'test-room',
        timestamp: new Date().toISOString()
      });
    }

    await waitFor(() => {
      // Should not show join notification for current user
      expect(screen.queryByText('user1 joined the chat')).not.toBeInTheDocument();
      // User count should remain 1
      expect(screen.getByText(/1 user online/)).toBeInTheDocument();
    });
  });

  it('should handle multiple users joining and leaving', async () => {
    const { useWebSocket } = await import('@/hooks/useWebSocket');
    const mockUseWebSocket = vi.mocked(useWebSocket);
    
    let onMessageCallback: ((message: any) => void) | undefined;
    
    mockUseWebSocket.mockImplementation((roomId, options) => {
      onMessageCallback = options?.onMessage;
      return {
        isConnected: true,
        isConnecting: false,
        error: null,
        sendMessage: mockSendMessage,
        reconnect: mockReconnect
      };
    });

    render(<ChatWindow {...defaultProps} />);

    // Simulate multiple users joining
    const users = ['user3', 'user4', 'user5'];
    
    for (const userId of users) {
      if (onMessageCallback) {
        onMessageCallback({
          type: 'user_join',
          user_id: userId,
          room_id: 'test-room',
          timestamp: new Date().toISOString()
        });
      }
    }

    await waitFor(() => {
      // Should show 4 users online (current user + 3 joined users)
      expect(screen.getByText(/4 users online/)).toBeInTheDocument();
      // Should show all join notifications
      expect(screen.getByText('user3 joined the chat')).toBeInTheDocument();
      expect(screen.getByText('user4 joined the chat')).toBeInTheDocument();
      expect(screen.getByText('user5 joined the chat')).toBeInTheDocument();
    });

    // Simulate one user leaving
    if (onMessageCallback) {
      onMessageCallback({
        type: 'user_leave',
        user_id: 'user4',
        room_id: 'test-room',
        timestamp: new Date().toISOString()
      });
    }

    await waitFor(() => {
      // Should show 3 users online now
      expect(screen.getByText(/3 users online/)).toBeInTheDocument();
      // Should show leave notification
      expect(screen.getByText('user4 left the chat')).toBeInTheDocument();
    });
  });

  it('should display correct singular/plural user count text', async () => {
    const { useWebSocket } = await import('@/hooks/useWebSocket');
    const mockUseWebSocket = vi.mocked(useWebSocket);
    
    let onMessageCallback: ((message: any) => void) | undefined;
    
    mockUseWebSocket.mockImplementation((roomId, options) => {
      onMessageCallback = options?.onMessage;
      return {
        isConnected: true,
        isConnecting: false,
        error: null,
        sendMessage: mockSendMessage,
        reconnect: mockReconnect
      };
    });

    render(<ChatWindow {...defaultProps} />);

    // Initially should show singular "user"
    expect(screen.getByText(/1 user online/)).toBeInTheDocument();

    // Add another user
    if (onMessageCallback) {
      onMessageCallback({
        type: 'user_join',
        user_id: 'user3',
        room_id: 'test-room',
        timestamp: new Date().toISOString()
      });
    }

    await waitFor(() => {
      // Should show plural "users"
      expect(screen.getByText(/2 users online/)).toBeInTheDocument();
    });

    // Remove the user
    if (onMessageCallback) {
      onMessageCallback({
        type: 'user_leave',
        user_id: 'user3',
        room_id: 'test-room',
        timestamp: new Date().toISOString()
      });
    }

    await waitFor(() => {
      // Should be back to singular "user"
      expect(screen.getByText(/1 user online/)).toBeInTheDocument();
    });
  });
});