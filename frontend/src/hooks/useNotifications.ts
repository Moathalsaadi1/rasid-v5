import { useCallback, useEffect, useState } from "react";
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../api/client";
import type { NotificationItem } from "../types";

const POLL_INTERVAL_MS = 30_000;

// Polls /api/notifications periodically while the tab is active and
// exposes mark-read helpers. Returns null while loading the first batch.
export function useNotifications(apiKey: string) {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const reload = useCallback(async () => {
    if (!apiKey) return;
    setLoading(true);
    try {
      const d = await listNotifications(apiKey);
      setItems(d.notifications);
      setUnreadCount(d.unread_count);
    } catch {
      // Silent — the bell will simply not update; failures here should
      // not interrupt the user's main workflow.
    } finally {
      setLoading(false);
    }
  }, [apiKey]);

  useEffect(() => {
    if (!apiKey) return;
    reload();
    const handle = setInterval(reload, POLL_INTERVAL_MS);
    const onFocus = () => reload();
    window.addEventListener("focus", onFocus);
    return () => {
      clearInterval(handle);
      window.removeEventListener("focus", onFocus);
    };
  }, [apiKey, reload]);

  const markRead = useCallback(
    async (id: number) => {
      await markNotificationRead(apiKey, id);
      await reload();
    },
    [apiKey, reload],
  );

  const markAllRead = useCallback(async () => {
    await markAllNotificationsRead(apiKey);
    await reload();
  }, [apiKey, reload]);

  return { items, unreadCount, loading, reload, markRead, markAllRead };
}
