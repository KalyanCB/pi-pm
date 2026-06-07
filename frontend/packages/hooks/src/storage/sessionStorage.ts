import AsyncStorage from '@react-native-async-storage/async-storage';
import type { StoredSession } from '@pipm/types';

const SESSION_KEY = '@pipm/session';

export async function loadSession(): Promise<StoredSession | null> {
  try {
    const raw = await AsyncStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as StoredSession;
  } catch {
    return null;
  }
}

export async function saveSession(session: StoredSession): Promise<void> {
  await AsyncStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export async function clearSessionStorage(): Promise<void> {
  await AsyncStorage.removeItem(SESSION_KEY);
}
