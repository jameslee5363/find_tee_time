import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import teeTimeService, { TeeTimeSearchRequest } from '../services/teeTime';
import '../styles/FindTeeTimes.css';

const FindTeeTimes: React.FC = () => {
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');

  const [formData, setFormData] = useState<TeeTimeSearchRequest>({
    course_name: '',
    preferred_dates: [],
    preferred_time_start: '',
    preferred_time_end: '',
    group_size: 1,
  });

  const [selectedDates, setSelectedDates] = useState<string[]>([]);
  const [dateInput, setDateInput] = useState<string>('');

  const availableCourses = [
    "Valley Brook 18",
    "Darlington 18",
    "Soldier Hill 18",
    "Overpeck 18",
    "Rockleigh R/W 18",
    "Orchard Hills",
    "Darlington Back 9",
    "Rockleigh Back 9",
    "Valley Brook 9",
    "Rockleigh Blue 9",
    "Soldier Hill Back 9",
    "Overpeck Back 9"
  ];

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'group_size' ? parseInt(value) || 1 : value,
    }));
  };

  const handleAddDate = () => {
    if (dateInput && !selectedDates.includes(dateInput)) {
      const newDates = [...selectedDates, dateInput].sort();
      setSelectedDates(newDates);
      setFormData(prev => ({
        ...prev,
        preferred_dates: newDates,
      }));
      setDateInput('');
    }
  };

  const handleRemoveDate = (dateToRemove: string) => {
    const newDates = selectedDates.filter(date => date !== dateToRemove);
    setSelectedDates(newDates);
    setFormData(prev => ({
      ...prev,
      preferred_dates: newDates,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setIsSubmitting(true);

    try {
      // Validate form
      if (!formData.course_name.trim()) {
        throw new Error('Please enter a course name');
      }

      if (formData.preferred_dates.length === 0) {
        throw new Error('Please select at least one date');
      }

      if (formData.group_size < 1 || formData.group_size > 4) {
        throw new Error('Group size must be between 1 and 4');
      }

      // Submit search request
      const response = await teeTimeService.createSearch({
        course_name: formData.course_name,
        preferred_dates: formData.preferred_dates,
        preferred_time_start: formData.preferred_time_start || undefined,
        preferred_time_end: formData.preferred_time_end || undefined,
        group_size: formData.group_size,
      });

      setSuccess('Your tee time search has been submitted successfully!');

      // Reset form after successful submission
      setTimeout(() => {
        setFormData({
          course_name: '',
          preferred_dates: [],
          preferred_time_start: '',
          preferred_time_end: '',
          group_size: 1,
        });
        setSelectedDates([]);
        navigate('/dashboard');
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'An error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBackToDashboard = () => {
    navigate('/dashboard');
  };

  return (
    <div className="find-tee-times-container">
      <div className="find-tee-times-header">
        <button onClick={handleBackToDashboard} className="back-button">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M19 12H5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M12 19L5 12L12 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Back to Dashboard
        </button>
        <h1>Find Tee Times</h1>
        <p>Tell us what you're looking for and we'll search for available tee times</p>
      </div>

      <div className="find-tee-times-content">
        <form onSubmit={handleSubmit} className="tee-time-form">
          {error && (
            <div className="alert alert-error">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
                <line x1="12" y1="8" x2="12" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <circle cx="12" cy="16" r="1" fill="currentColor"/>
              </svg>
              {error}
            </div>
          )}

          {success && (
            <div className="alert alert-success">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M22 11.08V12C21.9988 14.1564 21.3005 16.2547 20.0093 17.9818C18.7182 19.709 16.9033 20.9725 14.8354 21.5839C12.7674 22.1953 10.5573 22.1219 8.53447 21.3746C6.51168 20.6273 4.78465 19.2461 3.61096 17.4371C2.43727 15.628 1.87979 13.4881 2.02168 11.3363C2.16356 9.18455 2.99721 7.13631 4.39828 5.49706C5.79935 3.85781 7.69279 2.71537 9.79619 2.24013C11.8996 1.7649 14.1003 1.98232 16.07 2.85999" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M22 4L12 14.01L9 11.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              {success}
            </div>
          )}

          <div className="form-section">
            <h2>Course Information</h2>

            <div className="form-group">
              <label htmlFor="course_name">
                Course Name <span className="required">*</span>
              </label>
              <select
                id="course_name"
                name="course_name"
                value={formData.course_name}
                onChange={handleInputChange}
                required
              >
                <option value="">Select a course...</option>
                {availableCourses.map(course => (
                  <option key={course} value={course}>
                    {course}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-section">
            <h2>Preferred Dates</h2>

            <div className="form-group">
              <label htmlFor="date_input">
                Select Dates <span className="required">*</span>
              </label>
              <div className="date-input-group">
                <input
                  type="date"
                  id="date_input"
                  value={dateInput}
                  onChange={(e) => setDateInput(e.target.value)}
                  min={new Date().toISOString().split('T')[0]}
                />
                <button
                  type="button"
                  onClick={handleAddDate}
                  className="add-date-button"
                  disabled={!dateInput}
                >
                  Add Date
                </button>
              </div>
            </div>

            {selectedDates.length > 0 && (
              <div className="selected-dates">
                <label>Selected Dates:</label>
                <div className="date-chips">
                  {selectedDates.map(date => (
                    <div key={date} className="date-chip">
                      <span>{new Date(date + 'T12:00:00').toLocaleDateString('en-US', {
                        weekday: 'short',
                        month: 'short',
                        day: 'numeric'
                      })}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveDate(date)}
                        className="remove-date-button"
                        aria-label="Remove date"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="form-section">
            <h2>Time Preferences (Eastern Time)</h2>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="preferred_time_start">
                  Earliest Time
                </label>
                <input
                  type="time"
                  id="preferred_time_start"
                  name="preferred_time_start"
                  value={formData.preferred_time_start}
                  onChange={handleInputChange}
                />
                <span className="field-hint">Leave blank for any time</span>
              </div>

              <div className="form-group">
                <label htmlFor="preferred_time_end">
                  Latest Time
                </label>
                <input
                  type="time"
                  id="preferred_time_end"
                  name="preferred_time_end"
                  value={formData.preferred_time_end}
                  onChange={handleInputChange}
                />
                <span className="field-hint">Leave blank for any time</span>
              </div>
            </div>
          </div>

          <div className="form-section">
            <h2>Group Details</h2>

            <div className="form-group">
              <label htmlFor="group_size">
                Group Size <span className="required">*</span>
              </label>
              <input
                type="number"
                id="group_size"
                name="group_size"
                value={formData.group_size}
                onChange={handleInputChange}
                min="1"
                max="4"
                required
              />
              <span className="field-hint">Number of players (1-4)</span>
            </div>
          </div>

          <div className="form-actions">
            <button
              type="button"
              onClick={handleBackToDashboard}
              className="cancel-button"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="submit-button"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <span className="spinner"></span>
                  Submitting...
                </>
              ) : (
                'Search for Tee Times'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default FindTeeTimes;
