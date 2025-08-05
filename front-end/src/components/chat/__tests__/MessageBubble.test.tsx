import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageBubble, Message, VoiceMessage, SystemMessage } from '../MessageBubble';

// Mock HTMLAudioElement
class MockAudioElement {
  src: string = '';
  currentTime: number = 0;
  duration: number = 30; // 30 seconds
  paused: boolean = true;
  
  addEventListener = vi.fn();
  removeEventListener = vi.fn();
  play = vi.fn().mockResolvedValue(undefined);
  pause = vi.fn();
  
  // Simulate events
  triggerEvent(eventType: string) {
    const listeners = this.addEventListener.mock.calls
      .filter(call => call[0] === eventType)
      .map(call => call[1]);
    
    listeners.forEach(listener => listener());
  }
}

// Mock URL.createObjectURL and revokeObjectURL
const mockCreateObjectURL = vi.fn(() => 'blob:mock-url');
const mockRevokeObjectURL = vi.fn();

describe('MessageBubble', () => {
  let mockAudio: MockAudioElement;

  beforeEach(() => {
    mockAudio = new MockAudioElement();
    global.HTMLAudioElement = vi.fn(() => mockAudio) as any;
    global.URL.createObjectURL = mockCreateObjectURL;
    global.URL.revokeObjectURL = mockRevokeObjectURL;
    
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Text Messages', () => {
    const textMessage: Message = {
      from: 'user1',
      to: 'user2',
      text: 'Hello world!',
      lang: 'en',
      timestamp: '2024-01-01T12:00:00Z',
      status: 'sent'
    };

    it('renders text message correctly', () => {
      render(<MessageBubble message={textMessage} isCurrentUser={false} />);
      
      expect(screen.getByText('Hello world!')).toBeInTheDocument();
    });

    it('shows timestamp when showTimestamp is true', () => {
      render(<MessageBubble message={textMessage} showTimestamp={true} />);
      
      expect(screen.getByText('12:00')).toBeInTheDocument();
    });

    it('shows status icon for current user messages', () => {
      render(<MessageBubble message={textMessage} isCurrentUser={true} />);
      
      // Should show sent status icon
      expect(screen.getByRole('img', { hidden: true })).toBeInTheDocument();
    });

    it('applies correct styling for current user', () => {
      render(<MessageBubble message={textMessage} isCurrentUser={true} />);
      
      const messageContainer = screen.getByText('Hello world!').closest('div');
      expect(messageContainer).toHaveClass('bg-message-user');
    });

    it('applies correct styling for other user', () => {
      render(<MessageBubble message={textMessage} isCurrentUser={false} />);
      
      const messageContainer = screen.getByText('Hello world!').closest('div');
      expect(messageContainer).toHaveClass('bg-message-other');
    });
  });

  describe('Voice Messages', () => {
    const voiceMessage: VoiceMessage = {
      from: 'user1',
      to: 'user2',
      type: 'voice',
      audioData: new ArrayBuffer(1024),
      duration: 30,
      timestamp: '2024-01-01T12:00:00Z',
      status: 'sent'
    };

    it('renders voice message with play button', () => {
      render(<MessageBubble message={voiceMessage} isCurrentUser={false} />);
      
      expect(screen.getByRole('button')).toBeInTheDocument();
      expect(screen.getByText('0:00 / 0:00')).toBeInTheDocument();
    });

    it('creates audio URL from ArrayBuffer', () => {
      render(<MessageBubble message={voiceMessage} isCurrentUser={false} />);
      
      expect(mockCreateObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    });

    it('plays audio when play button is clicked', async () => {
      const user = userEvent.setup();
      render(<MessageBubble message={voiceMessage} isCurrentUser={false} />);
      
      const playButton = screen.getByRole('button');
      await user.click(playButton);
      
      expect(mockAudio.play).toHaveBeenCalled();
    });

    it('pauses audio when pause button is clicked during playback', async () => {
      const user = userEvent.setup();
      render(<MessageBubble message={voiceMessage} isCurrentUser={false} />);
      
      const playButton = screen.getByRole('button');
      
      // Start playing
      await user.click(playButton);
      mockAudio.paused = false;
      mockAudio.triggerEvent('play');
      
      await waitFor(() => {
        expect(screen.getByRole('button')).toBeInTheDocument();
      });
      
      // Pause
      await user.click(playButton);
      expect(mockAudio.pause).toHaveBeenCalled();
    });

    it('updates progress bar during playback', async () => {
      render(<MessageBubble message={voiceMessage} isCurrentUser={false} />);
      
      // Simulate audio metadata loaded
      mockAudio.duration = 30;
      mockAudio.triggerEvent('loadedmetadata');
      
      // Simulate time update
      mockAudio.currentTime = 15;
      mockAudio.triggerEvent('timeupdate');
      
      await waitFor(() => {
        expect(screen.getByText('0:15 / 0:30')).toBeInTheDocument();
      });
    });

    it('resets to beginning when audio ends', async () => {
      render(<MessageBubble message={voiceMessage} isCurrentUser={false} />);
      
      // Simulate audio ending
      mockAudio.triggerEvent('ended');
      
      await waitFor(() => {
        expect(screen.getByText('0:00')).toBeInTheDocument();
      });
    });

    it('shows error message when audio fails to load', async () => {
      render(<MessageBubble message={voiceMessage} isCurrentUser={false} />);
      
      // Simulate audio error
      mockAudio.triggerEvent('error');
      
      await waitFor(() => {
        expect(screen.getByText('Failed to load audio')).toBeInTheDocument();
      });
    });

    it('cleans up audio URL on unmount', () => {
      const { unmount } = render(<MessageBubble message={voiceMessage} isCurrentUser={false} />);
      
      unmount();
      
      expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
    });

    it('shows timestamp for voice messages when showTimestamp is true', () => {
      render(<MessageBubble message={voiceMessage} showTimestamp={true} />);
      
      expect(screen.getByText('12:00')).toBeInTheDocument();
    });

    it('shows status icon for current user voice messages', () => {
      render(<MessageBubble message={voiceMessage} isCurrentUser={true} />);
      
      // Should show sent status icon
      expect(screen.getByRole('img', { hidden: true })).toBeInTheDocument();
    });
  });

  describe('System Messages', () => {
    const systemMessage: SystemMessage = {
      type: 'system',
      content: 'User joined the chat',
      timestamp: '2024-01-01T12:00:00Z'
    };

    it('renders system message correctly', () => {
      render(<MessageBubble message={systemMessage} />);
      
      expect(screen.getByText('User joined the chat')).toBeInTheDocument();
    });

    it('shows timestamp for system messages when showTimestamp is true', () => {
      render(<MessageBubble message={systemMessage} showTimestamp={true} />);
      
      expect(screen.getByText('12:00')).toBeInTheDocument();
    });

    it('applies correct styling for system messages', () => {
      render(<MessageBubble message={systemMessage} />);
      
      const messageContainer = screen.getByText('User joined the chat').closest('div');
      expect(messageContainer).toHaveClass('bg-muted/50');
    });
  });

  describe('Message Status', () => {
    it('shows sending status', () => {
      const sendingMessage: Message = {
        from: 'user1',
        to: 'user2',
        text: 'Hello',
        lang: 'en',
        timestamp: '2024-01-01T12:00:00Z',
        status: 'sending'
      };

      render(<MessageBubble message={sendingMessage} isCurrentUser={true} />);
      
      // Should show clock icon for sending status
      expect(screen.getByRole('img', { hidden: true })).toBeInTheDocument();
    });

    it('shows delivered status', () => {
      const deliveredMessage: Message = {
        from: 'user1',
        to: 'user2',
        text: 'Hello',
        lang: 'en',
        timestamp: '2024-01-01T12:00:00Z',
        status: 'delivered'
      };

      render(<MessageBubble message={deliveredMessage} isCurrentUser={true} />);
      
      // Should show double check icon for delivered status
      expect(screen.getByRole('img', { hidden: true })).toBeInTheDocument();
    });
  });
});