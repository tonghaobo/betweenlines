/**
 * 简单的客户端缓存工具（V1 可选）
 * 对相同聊天内容在 5 分钟内返回缓存结果，减少 API 调用
 */

interface CacheEntry {
  data: unknown;
  timestamp: number;
}

const cache = new Map<string, CacheEntry>();
const CACHE_TTL = 5 * 60 * 1000; // 5 分钟

function hashString(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return hash.toString(36);
}

export function getCached(key: string): unknown | null {
  const hashedKey = hashString(key);
  const entry = cache.get(hashedKey);
  
  if (!entry) return null;
  
  if (Date.now() - entry.timestamp > CACHE_TTL) {
    cache.delete(hashedKey);
    return null;
  }
  
  return entry.data;
}

export function setCache(key: string, data: unknown): void {
  const hashedKey = hashString(key);
  cache.set(hashedKey, { data, timestamp: Date.now() });
}
