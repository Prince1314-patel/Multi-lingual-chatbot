import { render, screen, fireEvent } from '@testing-library/react';
import { MessageBubble, Message, VoiceMessage } from '../MessageBubble';
import { vi } from 'vitest';

describe('Message Delivery Confirmation', () => {
  const mockOnRetry = vi.fn();

  beforeEach(() => {
    mockOnRetry.mockClear();
  });

  describe('Message Status Icons', () => {
    it('shows sending status with clock icon', () => {
      const message: Message = {
        id: 'test-1',
        from: 'user1',
        to: 'user2',
        text: 'Hello',
        lang: 'en',
        timestamp: '2023-01-01T12:00:00Z',
        status: 'sending'
      };

      render(<MessageBubble message={message} isCurrentUser={true} onRetry={mockOnRetry} />);
      
      // Should show clock icon for sending status
      const clockIcon = screen.getByTestId('status-icon');
      expect(clockIcon).toBeInTheDocument();
      expect(clockIcon).toHaveClass('lucide-clock');
    });

    it('shows sent status with single check icon', () => {
      const message: Message = {
        id: 'test-2',
        from: 'user1',
        to: 'user2',
        text: 'Hello',
        lang: 'en',
        timestamp: '2023-01-01T12:00:00Z',
        status: 'sent'
      };

      render(<MessageBubble message={message} isCurrentUser={true} onRetry={mockOnRetry} />);
      
      // Should show single check icon for sent status
      const checkIcon = screen.getByTestId('status-icon');
      expect(checkIcon).toBeInTheDocument();
      expect(checkIcon).toHaveClass('lucide-check');
    });

    it('shows delivered status with double check icon', () => {
      const message: Message = {
        id: 'test-3',
        from: 'user1',
        to: 'user2',
        text: 'Hello',
        lang: 'en',
        timestamp: '2023-01-01T12:00:00Z',
        status: 'delivered'
      };

      render(<MessageBubble message={message} isCurrentUser={true} onRetry={mockOnRetry} />);
      
      // Should show double check icon for delivered status
      const checkIcon = screen.getByTestId('status-icon');
      expect(checkIcon).toBeInTheDocument();
      expect(checkIcon).toHaveClass('lucide-check-check');
    });

    it('shows failed status with error icon and retry button', () => {
      const message: Message = {
        id: 'test-4',
        from: 'user1',
        to: 'user2',
        text: 'Hello',
        lang: 'en',
        timestamp: '2023-01-01T12:00:00Z',
        status: 'failed'
      };

      render(<MessageBubble message={message} isCurrentUser={true} onRetry={mockOnRetry} />);
      
      // Should show error icon for failed status
      const statusContainer = screen.getByTestId('status-icon');
      expect(statusContainer).toBeInTheDocument();
      
      // Should show retry button
      const retryButton = screen.getByTestId('retry-button');
      expect(retryButton).toBeInTheDocument();
    });

    it('calls onRetry when retry button is clicked', () => {
      const message: Message = {
        id: 'test-5',
        from: 'user1',
        to: 'user2',
        text: 'Hello',
        lang: 'en',
        timestamp: '2023-01-01T12:00:00Z',
        status: 'failed'
      };

      render(<MessageBubble message={message} isCurrentUser={true} onRetry={mockOnRetry} />);
      
      const retryButton = screen.getByTestId('retry-button');
      fireEvent.click(retryButton);
      
      expect(mockOnRetry).toHaveBeenCalledWith(message);
    });

    it('does not show retry button when onRetry is not provided', () => {
      const message: Message = {
        id: 'test-6',
        from: 'user1',
        to: 'user2',
        text: 'Hello',
        lang: 'en',
        timestamp: '2023-01-01T12:00:00Z',
        status: 'failed'
      };

      render(<MessageBubble message={message} isCurrentUser={true} />);
      
      // Should show error icon but no retry button
      const statusContainer = screen.getByTestId('status-icon');
      expect(statusContainer).toBeInTheDocument();
      
      expect(screen.queryByTestId('retry-button')).not.toBeInTheDocument();
    });

    it('does not show status icons for other users messages', () => {
      const message: Message = {
        id: 'test-7',
        from: 'user2',
        to: 'user1',
        text: 'Hello',
        lang: 'en',
        timestamp: '2023-01-01T12:00:00Z',
        status: 'delivered'
      };

      render(<MessageBubble message={message} isCurrentUser={false} onRetry={mockOnRetry} />);
      
      // Should not show status icon for other users
      expect(screen.queryByTestId('status-icon')).not.toBeInTheDocument();
    });
  });

  describe('Voice Message Status', () => {
    it('shows status icons for voice messages', () => {
      const voiceMessage: VoiceMessage = {
        id: 'voice-1',
        from: 'user1',
        to: 'user2',
        type: 'voice',
        audioData: new ArrayBuffer(100),
        timestamp: '2023-01-01T12:00:00Z',
        status: 'delivered'
      };

      render(<MessageBubble message={voiceMessage} isCurrentUser={true} onRetry={mockOnRetry} />);
      
      // Should show double check icon for delivered voice message
      const checkIcon = screen.getByTestId('status-icon');
      expect(checkIcon).toBeInTheDocument();
      expect(checkIcon).toHaveClass('lucide-check-check');
    });

    it('shows retry button for failed voice messages', () => {
      const voiceMessage: VoiceMessage = {
        id: 'voice-2',
        from: 'user1',
        to: 'user2',
        type: 'voice',
        audioData: new ArrayBuffer(100),
        timestamp: '2023-01-01T12:00:00Z',
        status: 'failed'
      };

      render(<MessageBubble message={voiceMessage} isCurrentUser={true} onRetry={mockOnRetry} />);
      
      // Should show error icon and retry button
      const statusContainer = screen.getByTestId('status-icon');
      expect(statusContainer).toBeInTheDocument();
      
      const retryButton = screen.getByTestId('retry-button');
      expect(retryButton).toBeInTheDocument();
      
      fireEvent.click(retryButton);
      expect(mockOnRetry).toHaveBeenCalledWith(voiceMessage);
    });
  });
});