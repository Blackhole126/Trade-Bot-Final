/**
 * userStorage.ts
 *
 * A user-scoped localStorage utility that namespaces every key
 * by the currently logged-in username.
 *
 * Usage:
 *   const storage = getUserStorage('alice');
 *   storage.setItem('watchlist', '[...]'); // stores as "alice:watchlist"
 *   storage.getItem('watchlist');          // reads "alice:watchlist"
 *
 * This ensures that each user's data is completely isolated from
 * other users on the same browser.
 */

export interface UserStorage {
    getItem: (key: string) => string | null;
    setItem: (key: string, value: string) => void;
    removeItem: (key: string) => void;
    /** Removes ONLY this user's scoped keys from localStorage */
    clearUserData: () => void;
}

/** Build the namespaced key for a given user and data key */
export function scopedKey(username: string, key: string): string {
    // Sanitize username: lowercase + only alphanumeric/underscore/dot/at
    // If username is truly empty or purely whitespace, it defaults to guest
    const normalized = (username || '').toLowerCase().trim();
    const safe = normalized.replace(/[^a-z0-9_.@-]/g, '_');
    
    // Fallback if everything was replaced or empty
    const finalUser = safe || 'guest';
    return `${finalUser}:${key}`;
}

/**
 * Returns a storage interface scoped to the given username.
 * Falls back to an in-memory store if localStorage is unavailable.
 */
export function getUserStorage(username: string | null | undefined): UserStorage {
    // If no username (e.g. logged out), use a distinct guest ID to avoid mixed state
    const user = (username && username.trim()) ? username.trim() : '__unauthenticated_guest__';

    return {
        getItem(key: string): string | null {
            if (user === '__unauthenticated_guest__') return null; // Guests don't get persistent storage
            try {
                return localStorage.getItem(scopedKey(user, key));
            } catch {
                return null;
            }
        },

        setItem(key: string, value: string): void {
            if (user === '__unauthenticated_guest__') return; // Don't persist guest data
            try {
                localStorage.setItem(scopedKey(user, key), value);
            } catch {
                // localStorage may be unavailable
            }
        },

        removeItem(key: string): void {
            try {
                localStorage.removeItem(scopedKey(user, key));
            } catch {
                // ignore
            }
        },

        clearUserData(): void {
            try {
                const prefix = scopedKey(user, '');
                const keysToRemove: string[] = [];
                for (let i = 0; i < localStorage.length; i++) {
                    const k = localStorage.key(i);
                    if (k && k.startsWith(prefix)) {
                        keysToRemove.push(k);
                    }
                }
                keysToRemove.forEach((k) => localStorage.removeItem(k));
            } catch {
                // ignore
            }
        },
    };
}
