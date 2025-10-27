import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authService, { User } from '../services/auth';
import teeTimeService, { TeeTimeSearchResponse } from '../services/teeTime';
import notificationService, { TeeTimeNotification } from '../services/notifications';
import TeeTimeFoundModal from '../components/TeeTimeFoundModal';
import '../styles/Dashboard.css';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [searches, setSearches] = useState<TeeTimeSearchResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<TeeTimeNotification[]>([]);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    const currentUser = authService.getCurrentUser();
    if (!currentUser) {
      navigate('/login');
      return;
    }
    setUser(currentUser);
    loadSearches();
    checkForNotifications();

    // Poll for notifications every 30 seconds
    const pollInterval = setInterval(() => {
      checkForNotifications();
    }, 30000);

    return () => clearInterval(pollInterval);
  }, [navigate]);

  const loadSearches = async () => {
    try {
      setLoading(true);
      const userSearches = await teeTimeService.getUserSearches();
      // Filter to show only active searches
      const activeSearches = userSearches.filter(
        s => s.status !== 'cancelled' && s.status !== 'completed'
      );
      setSearches(activeSearches);
      setError(null);
    } catch (err) {
      console.error('Failed to load searches:', err);
      setError('Failed to load your searches');
    } finally {
      setLoading(false);
    }
  };

  const checkForNotifications = async () => {
    try {
      const unacknowledged = await notificationService.getUnacknowledgedNotifications();
      if (unacknowledged.length > 0) {
        setNotifications(unacknowledged);
        setShowModal(true);
      }
    } catch (err) {
      console.error('Failed to check notifications:', err);
    }
  };

  const handleNotificationAction = async (action: 'booked' | 'keep_searching' | 'no_longer_available') => {
    try {
      const notificationIds = notifications.map(n => n.id);
      await notificationService.acknowledgeNotifications({
        notification_ids: notificationIds,
        action
      });

      // Reload searches to reflect the updated status
      await loadSearches();

      // Close modal and clear notifications
      setShowModal(false);
      setNotifications([]);

      // Show success message
      if (action === 'booked') {
        alert('Great! Your search has been completed.');
      } else if (action === 'no_longer_available') {
        alert("We'll keep searching for you!");
      }
    } catch (err) {
      console.error('Failed to acknowledge notifications:', err);
      alert('Failed to process your action. Please try again.');
    }
  };

  const handleCancelSearch = async (searchId: number) => {
    if (!window.confirm('Are you sure you want to cancel this search?')) {
      return;
    }

    try {
      await teeTimeService.cancelSearch(searchId);
      setSearches(searches.filter(s => s.id !== searchId));
    } catch (err) {
      console.error('Failed to cancel search:', err);
      alert('Failed to cancel search. Please try again.');
    }
  };

  const parsePreferredDates = (datesJson: string): string[] => {
    try {
      return JSON.parse(datesJson);
    } catch {
      return [];
    }
  };

  const getStatusBadgeClass = (status: string): string => {
    switch (status) {
      case 'pending':
        return 'status-pending';
      case 'processing':
        return 'status-processing';
      case 'found_keep_searching':
        return 'status-found';
      default:
        return 'status-default';
    }
  };

  const getStatusLabel = (status: string): string => {
    switch (status) {
      case 'pending':
        return 'Searching...';
      case 'processing':
        return 'Processing';
      case 'found_keep_searching':
        return 'Found - Still Searching';
      default:
        return status;
    }
  };

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  if (!user) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <>
      {showModal && notifications.length > 0 && (
        <TeeTimeFoundModal
          notifications={notifications}
          onClose={handleNotificationAction}
        />
      )}
      <div className="dashboard-container">
      <nav className="dashboard-nav">
        <div className="nav-content">
          <div className="nav-logo">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M2 17L12 22L22 17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M2 12L12 17L22 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <span>Tee Time Finder</span>
          </div>
          <button onClick={handleLogout} className="logout-button">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M9 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M16 17L21 12L16 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M21 12H9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Logout
          </button>
        </div>
      </nav>

      <div className="dashboard-content">
        <div className="welcome-section">
          <h1>Welcome back{user.first_name ? `, ${user.first_name}` : ''}!</h1>
          <p>Ready to find your perfect tee time?</p>
        </div>

        {/* Active Searches Section */}
        <div className="active-searches-section">
          <div className="section-header">
            <h2>Active Tee Time Searches</h2>
            <button className="btn-primary" onClick={() => navigate('/find-tee-times')}>
              + New Search
            </button>
          </div>

          {loading && <div className="loading-text">Loading searches...</div>}
          {error && <div className="error-text">{error}</div>}

          {!loading && !error && searches.length === 0 && (
            <div className="empty-state">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2"/>
                <path d="M21 21L16.65 16.65" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
              <h3>No active searches</h3>
              <p>Create a new search to get notified when tee times become available</p>
              <button className="btn-primary" onClick={() => navigate('/find-tee-times')}>
                Create Your First Search
              </button>
            </div>
          )}

          {!loading && !error && searches.length > 0 && (
            <div className="searches-grid">
              {searches.map((search) => {
                const dates = parsePreferredDates(search.preferred_dates);
                return (
                  <div key={search.id} className="search-card">
                    <div className="search-card-header">
                      <div>
                        <h3>{search.course_name}</h3>
                        <span className={`search-status-badge ${getStatusBadgeClass(search.status)}`}>
                          {getStatusLabel(search.status)}
                        </span>
                      </div>
                    </div>
                    <div className="search-card-body">
                      <div className="search-detail">
                        <strong>Dates:</strong> {dates.join(', ')}
                      </div>
                      {search.preferred_time_start && search.preferred_time_end && (
                        <div className="search-detail">
                          <strong>Time:</strong> {search.preferred_time_start} - {search.preferred_time_end} ET
                        </div>
                      )}
                      <div className="search-detail">
                        <strong>Group Size:</strong> {search.group_size} player{search.group_size > 1 ? 's' : ''}
                      </div>
                      <div className="search-detail">
                        <strong>Created:</strong> {new Date(search.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="search-card-actions">
                      <button
                        className="btn-cancel"
                        onClick={() => handleCancelSearch(search.id)}
                        title="Cancel this search">
                        Cancel Search
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="user-card">
          <div className="user-card-header">
            <div className="user-avatar">
              {user.first_name?.[0] || user.email[0].toUpperCase()}
            </div>
            <div className="user-info">
              <h3>{user.first_name && user.last_name ? `${user.first_name} ${user.last_name}` : 'User'}</h3>
              <p>{user.email}</p>
            </div>
          </div>
          <div className="user-card-body">
            <div className="user-detail">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M22 16.92V19.92C22.0011 20.1985 21.9441 20.4742 21.8325 20.7293C21.7209 20.9845 21.5573 21.2136 21.3521 21.4019C21.1468 21.5901 20.9046 21.7335 20.6407 21.8227C20.3769 21.9119 20.0974 21.9451 19.82 21.92C16.7428 21.5856 13.787 20.5341 11.19 18.85C8.77382 17.3147 6.72533 15.2662 5.18999 12.85C3.49997 10.2412 2.44824 7.27099 2.11999 4.18C2.095 3.90347 2.12787 3.62476 2.21649 3.36162C2.30512 3.09849 2.44756 2.85669 2.63476 2.65162C2.82196 2.44655 3.0498 2.28271 3.30379 2.17052C3.55777 2.05833 3.83233 2.00026 4.10999 2H7.10999C7.5953 1.99522 8.06579 2.16708 8.43376 2.48353C8.80173 2.79999 9.04207 3.23945 9.10999 3.72C9.23662 4.68007 9.47144 5.62273 9.80999 6.53C9.94454 6.88792 9.97366 7.27691 9.8939 7.65088C9.81415 8.02485 9.62886 8.36811 9.35999 8.64L8.08999 9.91C9.51355 12.4135 11.5864 14.4864 14.09 15.91L15.36 14.64C15.6319 14.3711 15.9751 14.1858 16.3491 14.1061C16.7231 14.0263 17.1121 14.0555 17.47 14.19C18.3773 14.5286 19.3199 14.7634 20.28 14.89C20.7658 14.9585 21.2094 15.2032 21.5265 15.5775C21.8437 15.9518 22.0122 16.4296 22 16.92Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span>{user.phone_number}</span>
            </div>
            <div className="user-detail">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <line x1="16" y1="2" x2="16" y2="6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <line x1="8" y1="2" x2="8" y2="6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <line x1="3" y1="10" x2="21" y2="10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span>Member since {new Date(user.created_at).toLocaleDateString()}</span>
            </div>
            <div className="user-status">
              <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                {user.is_active ? 'Active' : 'Inactive'}
              </span>
              <span className={`status-badge ${user.is_verified ? 'verified' : 'unverified'}`}>
                {user.is_verified ? 'Verified' : 'Unverified'}
              </span>
            </div>
          </div>
        </div>

        <div className="features-grid">
          <div className="feature-card clickable" onClick={() => navigate('/find-tee-times')}>
            <div className="feature-icon">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <polyline points="12 6 12 12 16 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h3>Find Tee Times</h3>
            <p>Search and book available tee times at your favorite courses</p>
            <button className="feature-button">Get Started →</button>
          </div>
        </div>
      </div>
    </div>
    </>
  );
};

export default Dashboard;
