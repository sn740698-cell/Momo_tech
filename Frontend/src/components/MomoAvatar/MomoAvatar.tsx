import React, { useState, useEffect } from 'react';
import { MomoExpression, MomoAnimation } from '../../types/momo';

interface MomoAvatarProps {
  expression?: MomoExpression;
  animation?: MomoAnimation;
  isThinking?: boolean;
  isSpeaking?: boolean;
  size?: number;
  interactive?: boolean;
  onExpressionChange?: (expr: MomoExpression) => void;
}

export const MomoAvatar: React.FC<MomoAvatarProps> = ({
  expression = 'normal',
  animation = 'none',
  isThinking = false,
  isSpeaking = false,
  size = 200,
  interactive = false,
  onExpressionChange,
}) => {
  const [blink, setBlink] = useState(false);
  const [talkFrame, setTalkFrame] = useState(0);

  // Dynamic mouth movement while speaking
  useEffect(() => {
    if (!isSpeaking) return;
    const interval = setInterval(() => {
      setTalkFrame((prev) => (prev + 1) % 4);
    }, 110);
    return () => clearInterval(interval);
  }, [isSpeaking]);

  // Periodic natural blinking
  useEffect(() => {
    const interval = setInterval(() => {
      setBlink(true);
      setTimeout(() => setBlink(false), 180);
    }, 4500);
    return () => clearInterval(interval);
  }, []);

  // Compute CSS animation transform
  let animClass = '';
  if (animation === 'nod') animClass = 'animate-bounce';
  else if (animation === 'tilt_left') animClass = '-rotate-6 transition-transform duration-300';
  else if (animation === 'tilt_right') animClass = 'rotate-6 transition-transform duration-300';
  else if (animation === 'celebrate' || animation === 'wave') animClass = 'animate-pulse scale-105';
  else if (animation === 'sleep') animClass = 'opacity-75 translate-y-1';

  if (isThinking) {
    animClass = 'animate-pulse';
  }

  // Render SVG facial features based on expression
  const renderEyes = () => {
    if (blink || expression === 'sleepy') {
      // Closed / sleepy eyes
      return (
        <g stroke="#34d399" strokeWidth="4" strokeLinecap="round">
          <line x1="45" y1="65" x2="75" y2="65" />
          <line x1="125" y1="65" x2="155" y2="65" />
        </g>
      );
    }

    switch (expression) {
      case 'happy':
        return (
          <g fill="none" stroke="#10b981" strokeWidth="5" strokeLinecap="round">
            <path d="M 45 70 Q 60 50 75 70" />
            <path d="M 125 70 Q 140 50 155 70" />
          </g>
        );
      case 'thinking':
        return (
          <g fill="#38bdf8">
            <circle cx="65" cy="58" r="14" />
            <circle cx="145" cy="58" r="14" />
            <circle cx="68" cy="55" r="4" fill="#ffffff" />
            <circle cx="148" cy="55" r="4" fill="#ffffff" />
          </g>
        );
      case 'confused':
        return (
          <g fill="#fbbf24">
            <circle cx="58" cy="65" r="18" />
            <circle cx="138" cy="65" r="8" />
            <circle cx="54" cy="61" r="5" fill="#ffffff" />
          </g>
        );
      case 'excited':
        return (
          <g fill="#f43f5e">
            {/* Star eyes */}
            <polygon points="60,45 65,58 78,58 67,66 71,79 60,71 49,79 53,66 42,58 55,58" fill="#ec4899" />
            <polygon points="140,45 145,58 158,58 147,66 151,79 140,71 129,79 133,66 122,58 135,58" fill="#ec4899" />
          </g>
        );
      case 'sad':
        return (
          <g fill="none" stroke="#60a5fa" strokeWidth="4" strokeLinecap="round">
            <path d="M 45 65 Q 60 78 75 65" />
            <path d="M 125 65 Q 140 78 155 65" />
            <circle cx="48" cy="85" r="4" fill="#38bdf8" />
          </g>
        );
      case 'playful':
        return (
          <g fill="#a855f7">
            {/* Left wink */}
            <path d="M 45 62 L 60 70 L 45 78" fill="none" stroke="#c084fc" strokeWidth="4" strokeLinecap="round" />
            {/* Right eye */}
            <circle cx="140" cy="68" r="14" />
            <circle cx="136" cy="64" r="4" fill="#ffffff" />
          </g>
        );
      default: // normal
        return (
          <g fill="#10b981">
            <circle cx="60" cy="65" r="15" />
            <circle cx="140" cy="65" r="15" />
            <circle cx="56" cy="61" r="5" fill="#ffffff" />
            <circle cx="136" cy="61" r="5" fill="#ffffff" />
          </g>
        );
    }
  };

  const renderMouth = () => {
    if (isSpeaking) {
      const mouthHeights = [4, 10, 16, 8];
      const ry = mouthHeights[talkFrame];
      return (
        <g fill="#10b981">
          <ellipse cx="100" cy="104" rx="14" ry={ry} />
        </g>
      );
    }

    switch (expression) {
      case 'happy':
        return (
          <g fill="#10b981">
            <path d="M 80 95 Q 100 120 120 95 Z" />
          </g>
        );
      case 'thinking':
        return <line x1="88" y1="105" x2="112" y2="105" stroke="#38bdf8" strokeWidth="4" strokeLinecap="round" />;
      case 'confused':
        return <path d="M 85 105 Q 95 98 105 108 Q 115 118 120 108" fill="none" stroke="#fbbf24" strokeWidth="4" strokeLinecap="round" />;
      case 'excited':
        return (
          <g fill="#ec4899">
            <path d="M 75 92 Q 100 130 125 92 Z" />
          </g>
        );
      case 'sad':
        return <path d="M 85 110 Q 100 95 115 110" fill="none" stroke="#60a5fa" strokeWidth="4" strokeLinecap="round" />;
      case 'playful':
        return (
          <g>
            <path d="M 85 96 Q 100 115 115 96" fill="none" stroke="#c084fc" strokeWidth="4" strokeLinecap="round" />
            <path d="M 98 104 Q 104 118 110 104 Z" fill="#f43f5e" />
          </g>
        );
      case 'sleepy':
        return <circle cx="100" cy="100" r="6" fill="none" stroke="#34d399" strokeWidth="3" />;
      default:
        return <path d="M 85 96 Q 100 115 115 96" fill="none" stroke="#10b981" strokeWidth="4" strokeLinecap="round" />;
    }
  };

  return (
    <div className="flex flex-col items-center select-none">
      {/* Avatar Container with glowing OLED aesthetic */}
      <div
        className={`relative flex items-center justify-center rounded-3xl bg-slate-900 border-2 border-slate-700 shadow-2xl p-4 transition-all duration-300 ${animClass}`}
        style={{ width: size, height: size * 0.85 }}
      >
        {/* Glowing Aura */}
        <div
          className="absolute -inset-1 rounded-3xl opacity-30 blur-lg transition-all duration-500 pointer-events-none"
          style={{
            background:
              expression === 'excited'
                ? 'radial-gradient(circle, #f43f5e, #8b5cf6)'
                : expression === 'thinking'
                ? 'radial-gradient(circle, #0ea5e9, #6366f1)'
                : 'radial-gradient(circle, #10b981, #059669)',
          }}
        />

        {/* OLED Face SVG Screen */}
        <svg
          viewBox="0 0 200 150"
          className="w-full h-full relative z-10 filter drop-shadow-[0_0_8px_rgba(16,185,129,0.6)]"
        >
          {/* Subtle grid lines mimicking pixel matrix */}
          <rect x="0" y="0" width="200" height="150" rx="16" fill="#090d16" />

          {/* Decorative Antenna Dot */}
          <circle cx="100" cy="14" r="3" fill="#334155" />

          {/* Facial Elements */}
          {renderEyes()}
          {renderMouth()}

          {/* Blushing cheeks for happy/playful */}
          {(expression === 'happy' || expression === 'playful') && (
            <g fill="#ec4899" opacity="0.4">
              <circle cx="34" cy="85" r="7" />
              <circle cx="166" cy="85" r="7" />
            </g>
          )}

          {/* Thinking bubble when thinking */}
          {isThinking && (
            <g fill="#38bdf8" opacity="0.8">
              <circle cx="170" cy="25" r="5" />
              <circle cx="182" cy="15" r="8" />
            </g>
          )}
        </svg>
      </div>

      {/* Mood & Animation Tag */}
      <div className="mt-3 flex items-center gap-2">
        <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-slate-800 text-emerald-400 border border-slate-700 uppercase tracking-wider flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          {expression}
        </span>
        {isSpeaking && (
          <span className="px-2.5 py-0.5 text-xs rounded-full bg-emerald-950 text-emerald-300 border border-emerald-700 animate-pulse flex items-center gap-1">
            <span>🔊 Speaking...</span>
          </span>
        )}
        {animation !== 'none' && (
          <span className="px-2 py-0.5 text-xs rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800">
            {animation}
          </span>
        )}
      </div>

      {/* Interactive Expression Selector if enabled */}
      {interactive && onExpressionChange && (
        <div className="mt-3 flex flex-wrap gap-1.5 justify-center max-w-xs">
          {(['normal', 'happy', 'thinking', 'confused', 'sleepy', 'excited', 'sad', 'playful'] as MomoExpression[]).map(
            (expr) => (
              <button
                key={expr}
                onClick={() => onExpressionChange(expr)}
                className={`px-2 py-1 text-xs rounded-lg transition-all ${
                  expression === expr
                    ? 'bg-emerald-600 text-white font-medium shadow-md shadow-emerald-900/40'
                    : 'bg-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-700'
                }`}
              >
                {expr}
              </button>
            )
          )}
        </div>
      )}
    </div>
  );
};
