import api from './api';

export interface TeeTimeSearchRequest {
  course_name: string;
  preferred_dates: string[];  // YYYY-MM-DD format
  preferred_time_start?: string;  // HH:MM format (will be converted to UTC)
  preferred_time_end?: string;  // HH:MM format (will be converted to UTC)
  group_size: number;
}

export interface TeeTimeSearchResponse {
  id: number;
  user_id: number;
  course_name: string;
  preferred_dates: string;  // JSON string
  preferred_time_start?: string;
  preferred_time_end?: string;
  group_size: number;
  status: string;
  created_at: string;
  updated_at: string;
}

/**
 * Convert Eastern time to UTC time
 * @param timeStr Time in HH:MM format (Eastern)
 * @param dateStr Date in YYYY-MM-DD format
 * @returns Time in HH:MM format (UTC)
 */
const convertEasternToUTC = (timeStr: string, dateStr: string): string => {
  // Create a date object in Eastern time
  const [hours, minutes] = timeStr.split(':').map(Number);
  const dateTime = new Date(`${dateStr}T${timeStr}:00-05:00`); // EST offset

  // Get UTC hours and minutes
  const utcHours = dateTime.getUTCHours().toString().padStart(2, '0');
  const utcMinutes = dateTime.getUTCMinutes().toString().padStart(2, '0');

  return `${utcHours}:${utcMinutes}`;
};

/**
 * Convert UTC time to Eastern time
 * @param timeStr Time in HH:MM format (UTC)
 * @returns Time in HH:MM format (Eastern)
 */
export const convertUTCToEastern = (timeStr: string, dateStr: string = '2024-01-01'): string => {
  const [hours, minutes] = timeStr.split(':').map(Number);
  const dateTime = new Date(`${dateStr}T${timeStr}:00Z`); // UTC

  // Convert to Eastern time string
  const easternTime = dateTime.toLocaleString('en-US', {
    timeZone: 'America/New_York',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });

  return easternTime;
};

class TeeTimeService {
  /**
   * Create a new tee time search request
   * Note: Times in the request are in Eastern time and will be converted to UTC
   */
  async createSearch(searchData: TeeTimeSearchRequest): Promise<TeeTimeSearchResponse> {
    // Convert Eastern times to UTC before sending to backend
    const utcSearchData = {
      ...searchData,
      preferred_time_start: searchData.preferred_time_start
        ? convertEasternToUTC(searchData.preferred_time_start, searchData.preferred_dates[0])
        : undefined,
      preferred_time_end: searchData.preferred_time_end
        ? convertEasternToUTC(searchData.preferred_time_end, searchData.preferred_dates[0])
        : undefined,
    };

    const response = await api.post<TeeTimeSearchResponse>(
      '/api/tee-times/search',
      utcSearchData
    );
    return response.data;
  }

  /**
   * Get all tee time searches for the current user
   */
  async getUserSearches(): Promise<TeeTimeSearchResponse[]> {
    const response = await api.get<TeeTimeSearchResponse[]>('/api/tee-times/search');
    return response.data;
  }

  /**
   * Get a specific tee time search by ID
   */
  async getSearchById(searchId: number): Promise<TeeTimeSearchResponse> {
    const response = await api.get<TeeTimeSearchResponse>(`/api/tee-times/search/${searchId}`);
    return response.data;
  }

  /**
   * Cancel a tee time search
   */
  async cancelSearch(searchId: number): Promise<void> {
    await api.delete(`/api/tee-times/search/${searchId}`);
  }

  /**
   * Update the status of a tee time search
   */
  async updateSearchStatus(searchId: number, newStatus: string): Promise<TeeTimeSearchResponse> {
    const response = await api.patch<TeeTimeSearchResponse>(
      `/api/tee-times/search/${searchId}/status`,
      null,
      { params: { new_status: newStatus } }
    );
    return response.data;
  }
}

const teeTimeService = new TeeTimeService();
export default teeTimeService;
