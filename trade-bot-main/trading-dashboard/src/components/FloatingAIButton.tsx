import { useState } from 'react';
import { MessageCircle } from 'lucide-react';
import AIChatPanel from './AIChatPanel';

const FloatingAIButton = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [imageError, setImageError] = useState(false);

  const handleOpen = () => {
    try {
      setIsOpen(true);
    } catch (error) {
      console.error('Error opening AI chat:', error);
    }
  };

  const handleClose = () => {
    try {
      setIsOpen(false);
    } catch (error) {
      console.error('Error closing AI chat:', error);
    }
  };

  return (
    <>
      {/* Floating Button */}
      <button
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={handleOpen}
        className={`fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-50 w-12 h-12 sm:w-14 sm:h-14 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center group touch-manipulation ${
          isHovered ? 'scale-110' : 'scale-100'
        }`}
        aria-label="AI Assistant"
      >
        <div className="relative w-6 h-6 sm:w-8 sm:h-8 flex items-center justify-center">
          {/* AI Logo */}
          {!imageError ? (
            <img
              src="/jarvis-logo.png"
              alt="AI Assistant"
              className="w-6 h-6 sm:w-8 sm:h-8 object-contain"
              onError={() => setImageError(true)}
            />
          ) : (
            <MessageCircle className="w-6 h-6 sm:w-8 sm:h-8 text-white" />
          )}
        </div>
        
        {/* Tooltip on hover - hidden on mobile */}
        {isHovered && (
          <div className="hidden sm:block absolute bottom-full right-0 mb-2 px-3 py-1.5 bg-slate-800 text-white text-xs rounded-lg shadow-lg whitespace-nowrap">
            AI Assistant
            <div className="absolute top-full right-4 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-slate-800"></div>
          </div>
        )}
      </button>

      {/* Chat Panel */}
      {isOpen && (
        <AIChatPanel
          onClose={handleClose}
          onMinimize={handleClose}
        />
      )}
    </>
  );
};

export default FloatingAIButton;

