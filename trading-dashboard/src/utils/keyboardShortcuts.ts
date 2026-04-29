/**
 * Keyboard shortcuts utility
 */

export interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  action: () => void;
  description: string;
}

const shortcuts: KeyboardShortcut[] = [];

export const registerShortcut = (shortcut: KeyboardShortcut): (() => void) => {
  shortcuts.push(shortcut);
  
  const handler = (e: KeyboardEvent) => {
    if (
      (shortcut.ctrlKey === undefined || e.ctrlKey === shortcut.ctrlKey) &&
      (shortcut.shiftKey === undefined || e.shiftKey === shortcut.shiftKey) &&
      (shortcut.altKey === undefined || e.altKey === shortcut.altKey) &&
      e.key.toLowerCase() === shortcut.key.toLowerCase()
    ) {
      // Don't trigger if user is typing in an input
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
      }
      
      e.preventDefault();
      shortcut.action();
    }
  };

  document.addEventListener('keydown', handler);
  
  // Return cleanup function
  return () => {
    document.removeEventListener('keydown', handler);
    const index = shortcuts.indexOf(shortcut);
    if (index > -1) {
      shortcuts.splice(index, 1);
    }
  };
};

// Common shortcuts
export const commonShortcuts = {
  refresh: (action: () => void) => registerShortcut({
    key: 'r',
    ctrlKey: true,
    action,
    description: 'Refresh data',
  }),
  search: (action: () => void) => registerShortcut({
    key: 'k',
    ctrlKey: true,
    action,
    description: 'Focus search',
  }),
  close: (action: () => void) => registerShortcut({
    key: 'Escape',
    action,
    description: 'Close modal/dialog',
  }),
};

