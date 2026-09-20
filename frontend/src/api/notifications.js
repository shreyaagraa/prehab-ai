import api from "./axios";

/**
 * Fetch paginated notifications for the current authenticated user.
 * @param {Object} params - { skip, limit, unread_only }
 */
export async function getNotifications(params = {}) {
    const { skip = 0, limit = 30, unread_only = false } = params;
    const response = await api.get("/notifications", {
        params: { skip, limit, unread_only },
    });
    return response.data;
}

/**
 * Fetch unread notification count for badge rendering.
 */
export async function getUnreadCount() {
    const response = await api.get("/notifications/unread-count");
    return response.data;
}

/**
 * Mark a single notification as read.
 * @param {string} notificationId
 */
export async function markAsRead(notificationId) {
    const response = await api.patch(`/notifications/${notificationId}/read`);
    return response.data;
}

/**
 * Mark all unread notifications for current user as read.
 */
export async function markAllAsRead() {
    const response = await api.patch("/notifications/read-all");
    return response.data;
}

/**
 * Dismiss / delete a single notification.
 * @param {string} notificationId
 */
export async function deleteNotification(notificationId) {
    const response = await api.delete(`/notifications/${notificationId}`);
    return response.data;
}
