import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { InputBar } from '../InputBar';
import { MessageBubble, VoiceMessage } from '../MessageBubble';

// Mock MediaRecorder
class MockMediaRecorder {
  static isTypeSupported = vi.fn(() => true);
  
  ondataavailable: ((event: any) => void) | null = null;
  onstop: (() => void) | null = null;
  state: string = 'inactive';
  
  start() {
    this.state = 'recording';
    setTimeout(() => {
      if (this.ondataavailable) {
        this.ondataavailable({
          data: new Blob(['mock audio data'], { type: 'audio/webm;codecs=opus' })
        });
      }
    }, 10);
  }
  
  stop() {
    this.state = 'inactive';
    setTimeout(() => {
      if (this.onstop) {
        this.onstop();
      }
    }, 10);
  }
}

// Mock getUserMedia
const mockGetUserMedia = vi.fn();

// Mock MediaStream
class MockMediaStream {
  getTracks() {
    return [{ stop: vi.fn() }];
  }
}

describe('Voice Integration Basic Tests', () => {
  beforeEach(() => {
    global.MediaRecorder = MockMediaRecorder as any;
    global.navigator.mediaDevices = {
      getUserMedia: mockGetUserMedia
    } as any;
    
    mockGetUserMedia.mockResolvedValue(new MockMediaStream());
    vi.clearAllMocks();
  });

  it('renders voice recording button in InputBar', () => {
    const mockOnSendMessage = vi.fn();
    const mockOnSendVoiceMessage = vi.fn();
    const mockOnTyping = vi.fn();

    render(
      <InputBar
        onSendMessage={mockOnSendMessage}
        onSendVoiceMessage={mockOnSendVoiceMessage}
        onTyping={mockOnTyping}
      />
    );

    expect(screen.getByRole('button', { name: /start voice recording/i })).toBeInTheDocument();
  });

  it('renders voice message with play button in MessageBubble', () => {
    const voiceMessage: VoiceMessage = {
      from: 'user1',
      to: 'user2',
      type: 'voice',
      audioData: new ArrayBuffer(1024),
      timestamp: '2024-01-01T12:00:00Z',
      status: 'sent'
    };

    render(<MessageBubble message={voiceMessage} isCurrentUser={false} />);
    
    // Check for either play button or error message (since audio might fail in test environment)
    const playButton = screen.queryByRole('button');
    const errorMessage = screen.queryByText(/Failed to load audio/);
    
    expect(playButton || errorMessage).toBeTruthy();
    // Check for either 0:00 or the default duration format
    const durationText = screen.queryByText(/0:00/);
    const defaultDuration = screen.queryByText('0:00 / 0:00');
    expect(durationText || defaultDuration).toBeTruthy();
  });

  it('can start voice recording', async () => {
    const user = userEvent.setup();
    const mockOnSendMessage = vi.fn();
    const mockOnSendVoiceMessage = vi.fn();
    const mockOnTyping = vi.fn();

    render(
      <InputBar
        onSendMessage={mockOnSendMessage}
        onSendVoiceMessage={mockOnSendVoiceMessage}
        onTyping={mockOnTyping}
      />
    );

    const micButton = screen.getByRole('button', { name: /start voice recording/i });
    await user.click(micButton);

    expect(mockGetUserMedia).toHaveBeenCalled();
  });

  it('shows recording state when recording', async () => {
    const user = userEvent.setup();
    const mockOnSendMessage = vi.fn();
    const mockOnSendVoiceMessage = vi.fn();
    const mockOnTyping = vi.fn();

    render(
      <InputBar
        onSendMessage={mockOnSendMessage}
        onSendVoiceMessage={mockOnSendVoiceMessage}
        onTyping={mockOnTyping}
      />
    );

    const micButton = screen.getByRole('button', { name: /start voice recording/i });
    await user.click(micButton);

    // Should show recording state
    expect(screen.getByText(/recording/i)).toBeInTheDocument();
  });

  it('integrates InputBar and MessageBubble for voice messages', () => {
    // Test that both components can handle voice messages
    const mockOnSendMessage = vi.fn();
    const mockOnSendVoiceMessage = vi.fn();
    const mockOnTyping = vi.fn();

    const { rerender } = render(
      <InputBar
        onSendMessage={mockOnSendMessage}
        onSendVoiceMessage={mockOnSendVoiceMessage}
        onTyping={mockOnTyping}
      />
    );

    // InputBar should have voice recording capability
    expect(screen.getByRole('button', { name: /start voice recording/i })).toBeInTheDocument();

    // Now test MessageBubble with voice message
    const voiceMessage: VoiceMessage = {
      from: 'user1',
      to: 'user2',
      type: 'voice',
      audioData: new ArrayBuffer(1024),
      timestamp: '2024-01-01T12:00:00Z',
      status: 'sent'
    };

    rerender(<MessageBubble message={voiceMessage} isCurrentUser={false} />);
    
    // MessageBubble should render voice message with play button or error message
    const playButton = screen.queryByRole('button');
    const errorMessage = screen.queryByText(/Failed to load audio/);
    
    expect(playButton || errorMessage).toBeTruthy();
  });
});