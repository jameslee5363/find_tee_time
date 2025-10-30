import api from './api';

export interface TeeTimeSearchRequest {
  course_names: string[];  // Array of course names
  preferred_dates: string[];  // YYYY-MM-DD format
  preferred_time_start?: string;  // HH:MM format (Eastern Time)
  preferred_time_end?: string;  // HH:MM format (Eastern Time)
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

// All times are stored and transmitted in Eastern Time (no conversion needed)

class TeeTimeService {
  /**
   * Create a new tee time search request
   * Note: All times are in Eastern Time
   */
  async createSearch(searchData: TeeTimeSearchRequest): Promise<TeeTimeSearchResponse> {
    // Send times as-is (Eastern Time)
    const response = await api.post<TeeTimeSearchResponse>(
      '/api/tee-times/search',
      searchData
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
