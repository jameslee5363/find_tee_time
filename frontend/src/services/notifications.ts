import api from './api';

export interface TeeTimeNotification {
  id: number;
  search_id: number;
  user_id: number;
  tee_time_id: string;
  course_name: string;
  tee_off_date: string;
  tee_off_time: string;
  available_spots: number;
  email_sent: boolean;
  notification_sent_at: string;
  user_acknowledged: boolean;
  user_action: string | null;
  created_at: string;
}

export interface AcknowledgeRequest {
  notification_ids: number[];
  action: 'booked' | 'keep_searching' | 'no_longer_available';
}

class NotificationService {
  /**
   * Get all unacknowledged notifications for the current user
   */
  async getUnacknowledgedNotifications(): Promise<TeeTimeNotification[]> {
    const response = await api.get<TeeTimeNotification[]>('/api/notifications/unacknowledged');
    return response.data;
  }

  /**
   * Acknowledge notifications and take action
   */
  async acknowledgeNotifications(request: AcknowledgeRequest): Promise<{ success: boolean; message: string; action_taken: string }> {
    const response = await api.post('/api/notifications/acknowledge', request);
    return response.data;
  }
}

const notificationService = new NotificationService();
export default notificationService;
