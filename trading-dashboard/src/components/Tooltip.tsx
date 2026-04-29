import { ReactNode } from 'react';

interface TooltipProps {
  children: ReactNode;
  content: string;
  position?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
}

export const Tooltip = ({ children, content, position = 'top', className = '' }: TooltipProps) => {
  return (
    <div className={`relative group ${className}`}>
      {children}
      <div className={`
        absolute z-50 px-2 py-1 text-xs text-white bg-slate-900 rounded shadow-lg
        opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all
        whitespace-nowrap pointer-events-none
        ${position === 'top' ? 'bottom-full left-1/2 -translate-x-1/2 mb-2' : ''}
        ${position === 'bottom' ? 'top-full left-1/2 -translate-x-1/2 mt-2' : ''}
        ${position === 'left' ? 'right-full top-1/2 -translate-y-1/2 mr-2' : ''}
        ${position === 'right' ? 'left-full top-1/2 -translate-y-1/2 ml-2' : ''}
      `}>
        {content}
        <div className={`
          absolute w-2 h-2 bg-slate-900 rotate-45
          ${position === 'top' ? 'top-full left-1/2 -translate-x-1/2 -mt-1' : ''}
          ${position === 'bottom' ? 'bottom-full left-1/2 -translate-x-1/2 -mb-1' : ''}
          ${position === 'left' ? 'left-full top-1/2 -translate-y-1/2 -ml-1' : ''}
          ${position === 'right' ? 'right-full top-1/2 -translate-y-1/2 -mr-1' : ''}
        `} />
      </div>
    </div>
  );
};

export default Tooltip;




