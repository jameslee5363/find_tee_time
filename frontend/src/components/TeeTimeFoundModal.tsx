import React, { useState } from 'react';
import { TeeTimeNotification } from '../services/notifications';
import '../styles/TeeTimeFoundModal.css';

interface TeeTimeFoundModalProps {
  notifications: TeeTimeNotification[];
  onClose: (action: 'booked' | 'keep_searching' | 'no_longer_available') => void;
}

const TeeTimeFoundModal: React.FC<TeeTimeFoundModalProps> = ({ notifications, onClose }) => {
  const [selectedAction, setSelectedAction] = useState<'booked' | 'keep_searching' | 'no_longer_available' | null>(null);

  if (notifications.length === 0) return null;

  // Group notifications by search_id
  const searchGroups = notifications.reduce((acc, notif) => {
    if (!acc[notif.search_id]) {
      acc[notif.search_id] = [];
    }
    acc[notif.search_id].push(notif);
    return acc;
  }, {} as Record<number, TeeTimeNotification[]>);

  const handleAction = (action: 'booked' | 'keep_searching' | 'no_longer_available') => {
    setSelectedAction(action);
    onClose(action);
  };

  return (
    <div className="modal-overlay">
      <div className="modal-container">
        <div className="modal-header">
          <div className="modal-icon">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
              <path d="M12 6v6l4 2" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <h2>Tee Time{notifications.length > 1 ? 's' : ''} Found!</h2>
          <p className="modal-subtitle">
            We found {notifications.length} matching tee time{notifications.length > 1 ? 's' : ''} for your search
          </p>
        </div>

        <div className="modal-body">
          {Object.entries(searchGroups).map(([searchId, searchNotifs]) => (
            <div key={searchId} className="search-group">
              <h3 className="search-title">Search #{searchId}</h3>
              <div className="tee-times-list">
                {searchNotifs.map((notif) => (
                  <div key={notif.id} className="tee-time-item">
                    <div className="tee-time-info">
                      <strong>{notif.course_name}</strong>
                      <div className="tee-time-details">
                        <span>{notif.tee_off_date}</span>
                        <span className="separator">•</span>
                        <span>{notif.tee_off_time} ET</span>
                        <span className="separator">•</span>
                        <span>{notif.available_spots} spot{notif.available_spots > 1 ? 's' : ''} available</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="modal-footer">
          <p className="footer-question">What would you like to do?</p>
          <div className="action-buttons">
            <button
              className="action-btn success-btn"
              onClick={() => handleAction('booked')}
              disabled={selectedAction !== null}
            >
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M20 6L9 17L4 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              I Booked My Tee Time
            </button>

            <button
              className="action-btn warning-btn"
              onClick={() => handleAction('no_longer_available')}
              disabled={selectedAction !== null}
            >
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
                <path d="M8 12h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
              No Longer Available - Keep Searching
            </button>
          </div>

          {selectedAction && (
            <div className="processing-message">
              Processing your choice...
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TeeTimeFoundModal;
