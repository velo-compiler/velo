import React from 'react';

interface VeloLogoProps {
  variant?: 'symbol' | 'tile' | 'horizontal';
  size?: number | string;
  className?: string;
  withGlow?: boolean;
}

export const VeloLogo: React.FC<VeloLogoProps> = ({
  variant = 'symbol',
  size = 32,
  className = '',
  withGlow = false,
}) => {
  // Left Wing (Keel / Stability)
  const leftPath = "M 76,112 L 180,112 L 244,272 L 214,404 L 172,404 L 76,192 Z";
  // Right Wing (Velocity Vector Blade)
  const rightPath = "M 268,212 L 336,88 L 436,88 L 280,432 L 236,432 L 254,308 Z";

  // Outlined Wordmark "Velo" paths
  const pV = "M 0,0 L 28,0 L 52,88 L 76,0 L 104,0 L 62,120 L 42,120 Z";
  const pE = "M 74,96 C 68,110 56,120 40,120 C 18,120 0,102 0,78 C 0,54 18,36 40,36 C 63,36 78,53 78,80 L 78,84 L 22,84 C 23,97 31,103 41,103 C 51,103 60,97 64,88 Z M 22,68 L 57,68 C 56,53 49,49 40,49 C 31,49 24,54 22,68 Z";
  const pL = "M 0,0 L 22,0 L 22,120 L 0,120 Z";
  const pO = "M 42,36 C 65.2,36 84,54.8 84,78 C 84,101.2 65.2,120 42,120 C 18.8,120 0,101.2 0,78 C 0,54.8 18.8,36 42,36 Z M 42,56 C 29.8,56 20,65.8 20,78 C 20,90.2 29.8,100 42,100 C 54.2,100 64,90.2 64,78 C 64,65.8 54.2,56 42,56 Z";

  if (variant === 'horizontal') {
    return (
      <svg
        viewBox="0 0 640 180"
        width={typeof size === 'number' ? size * 3.5 : size}
        height={size}
        className={`inline-block ${className}`}
        xmlns="http://www.w3.org/2000/svg"
        role="img"
        aria-label="Velo Programming Language"
      >
        <defs>
          <linearGradient id="veloCobaltH" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#1D4ED8" />
            <stop offset="100%" stopColor="#2563EB" />
          </linearGradient>
          <linearGradient id="veloCyanH" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00F0FF" />
            <stop offset="100%" stopColor="#0284C7" />
          </linearGradient>
        </defs>
        <g id="velo-horizontal-lockup">
          <g transform="translate(36, 26) scale(0.25)">
            <path d={leftPath} fill="url(#veloCobaltH)" />
            <path d={rightPath} fill="url(#veloCyanH)" />
          </g>
          <g transform="translate(196, 42) scale(0.8)" fill="#FFFFFF">
            <path d={pV} />
            <path transform="translate(112, 0)" d={pE} />
            <path transform="translate(206, 0)" d={pL} />
            <path transform="translate(242, 0)" d={pO} />
          </g>
        </g>
      </svg>
    );
  }

  if (variant === 'tile') {
    return (
      <div
        style={{ width: size, height: size }}
        className={`relative rounded-xl bg-gradient-to-tr from-cyan-950/80 to-blue-950/80 border border-cyan-500/30 flex items-center justify-center p-2 shadow-lg shadow-cyan-500/10 ${withGlow ? 'ring-2 ring-cyan-400/20 shadow-cyan-500/20' : ''} ${className}`}
      >
        <svg
          viewBox="0 0 512 512"
          className="w-full h-full"
          xmlns="http://www.w3.org/2000/svg"
          role="img"
          aria-label="Velo Mark"
        >
          <defs>
            <linearGradient id="veloCobaltTile" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#1D4ED8" />
              <stop offset="100%" stopColor="#2563EB" />
            </linearGradient>
            <linearGradient id="veloCyanTile" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#00F0FF" />
              <stop offset="100%" stopColor="#0284C7" />
            </linearGradient>
          </defs>
          <path d={leftPath} fill="url(#veloCobaltTile)" />
          <path d={rightPath} fill="url(#veloCyanTile)" />
        </svg>
      </div>
    );
  }

  // Pure SVG symbol
  return (
    <svg
      viewBox="0 0 512 512"
      width={size}
      height={size}
      className={`inline-block ${className}`}
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Velo Logo"
    >
      <defs>
        <linearGradient id="veloCobaltSym" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#1D4ED8" />
          <stop offset="100%" stopColor="#2563EB" />
        </linearGradient>
        <linearGradient id="veloCyanSym" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#00F0FF" />
          <stop offset="100%" stopColor="#0284C7" />
        </linearGradient>
      </defs>
      <path d={leftPath} fill="url(#veloCobaltSym)" />
      <path d={rightPath} fill="url(#veloCyanSym)" />
    </svg>
  );
};

