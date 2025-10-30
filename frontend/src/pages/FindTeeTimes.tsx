import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import teeTimeService from '../services/teeTime';
import '../styles/FindTeeTimes.css';

const FindTeeTimes: React.FC = () => {
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');

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

  const [selectedCourses, setSelectedCourses] = useState<string[]>([]);
  const [selectedDates, setSelectedDates] = useState<string[]>([]);
  const [dateInput, setDateInput] = useState<string>('');
  const [timeStart, setTimeStart] = useState<string>('');
  const [timeEnd, setTimeEnd] = useState<string>('');
  const [groupSize, setGroupSize] = useState<number>(1);

  const handleSelectAllCourses = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedCourses([...availableCourses]);
    } else {
      setSelectedCourses([]);
    }
  };

  const handleCourseChange = (course: string) => {
    if (selectedCourses.includes(course)) {
      setSelectedCourses(selectedCourses.filter(c => c !== course));
    } else {
      setSelectedCourses([...selectedCourses, course]);
    }
  };

  const handleAddDate = () => {
    if (dateInput && !selectedDates.includes(dateInput)) {
      const newDates = [...selectedDates, dateInput].sort();
      setSelectedDates(newDates);
      setDateInput('');
    }
  };

  const handleRemoveDate = (dateToRemove: string) => {
    setSelectedDates(selectedDates.filter(date => date !== dateToRemove));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setIsSubmitting(true);

    try {
      // Validate form
      if (selectedCourses.length === 0) {
        throw new Error('Please select at least one course');
      }

      if (selectedDates.length === 0) {
        throw new Error('Please select at least one date');
      }

      if (groupSize < 1 || groupSize > 4) {
        throw new Error('Group size must be between 1 and 4');
      }

      // Submit search request
      await teeTimeService.createSearch({
        course_names: selectedCourses,
        preferred_dates: selectedDates,
        preferred_time_start: timeStart || undefined,
        preferred_time_end: timeEnd || undefined,
        group_size: groupSize,
      });

      setSuccess('Your tee time search has been submitted successfully!');

      // Reset form after successful submission
      setTimeout(() => {
        setSelectedCourses([]);
        setSelectedDates([]);
        setTimeStart('');
        setTimeEnd('');
        setGroupSize(1);
        setSuccess('');
        navigate('/dashboard');
      }, 2000);
    } catch (err: any) {
      setError(err.message || 'Failed to submit search. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const allCoursesSelected = selectedCourses.length === availableCourses.length;

  return (
    <div className="find-tee-times-container">
      <div className="find-tee-times-header">
        <button onClick={() => navigate('/dashboard')} className="back-button">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M19 12H5M5 12L12 19M5 12L12 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Back to Dashboard
        </button>
        <h1>Find Your Perfect Tee Time</h1>
        <p>Set your preferences and we'll notify you when matching tee times become available</p>
      </div>

      <form onSubmit={handleSubmit} className="tee-time-form">
        {/* Course Selection */}
        <div className="form-group">
          <label className="form-label">
            Select Golf Courses
            <span className="required">*</span>
          </label>
          <div className="course-selection">
            <div className="select-all-wrapper">
              <label className="checkbox-label select-all-label">
                <input
                  type="checkbox"
                  checked={allCoursesSelected}
                  onChange={handleSelectAllCourses}
                />
                <span className="checkbox-text">Select All Courses</span>
              </label>
            </div>
            <div className="courses-grid">
              {availableCourses.map((course) => (
                <label key={course} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={selectedCourses.includes(course)}
                    onChange={() => handleCourseChange(course)}
                  />
                  <span className="checkbox-text">{course}</span>
                </label>
              ))}
            </div>
            {selectedCourses.length > 0 && (
              <div className="selected-count">
                {selectedCourses.length} course{selectedCourses.length > 1 ? 's' : ''} selected
              </div>
            )}
          </div>
        </div>

        {/* Date Selection */}
        <div className="form-group">
          <label className="form-label">
            Preferred Dates
            <span className="required">*</span>
          </label>
          <div className="date-input-wrapper">
            <input
              type="date"
              value={dateInput}
              onChange={(e) => setDateInput(e.target.value)}
              className="form-input"
              min={new Date().toISOString().split('T')[0]}
            />
            <button type="button" onClick={handleAddDate} className="add-date-button">
              Add Date
            </button>
          </div>
          {selectedDates.length > 0 && (
            <div className="selected-dates">
              {selectedDates.map((date) => (
                <div key={date} className="date-chip">
                  <span>{new Date(date + 'T00:00:00').toLocaleDateString()}</span>
                  <button type="button" onClick={() => handleRemoveDate(date)} className="remove-chip">
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Time Range (Optional) */}
        <div className="form-group">
          <label className="form-label">
            Preferred Time Range (Optional)
            <span className="hint">Times in Eastern Time</span>
          </label>
          <div className="time-range-wrapper">
            <div className="time-input-group">
              <label htmlFor="preferred_time_start">From</label>
              <input
                type="time"
                id="preferred_time_start"
                value={timeStart}
                onChange={(e) => setTimeStart(e.target.value)}
                className="form-input time-input"
              />
            </div>
            <span className="time-separator">to</span>
            <div className="time-input-group">
              <label htmlFor="preferred_time_end">To</label>
              <input
                type="time"
                id="preferred_time_end"
                value={timeEnd}
                onChange={(e) => setTimeEnd(e.target.value)}
                className="form-input time-input"
              />
            </div>
          </div>
        </div>

        {/* Group Size */}
        <div className="form-group">
          <label htmlFor="group_size" className="form-label">
            Group Size
            <span className="required">*</span>
          </label>
          <input
            type="number"
            id="group_size"
            value={groupSize}
            onChange={(e) => setGroupSize(parseInt(e.target.value) || 1)}
            min="1"
            max="4"
            className="form-input number-input"
            required
          />
          <p className="hint">Maximum 4 players per group</p>
        </div>

        {/* Error/Success Messages */}
        {error && (
          <div className="message error-message">
            {error}
          </div>
        )}

        {success && (
          <div className="message success-message">
            {success}
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isSubmitting || selectedCourses.length === 0 || selectedDates.length === 0}
          className="submit-button"
        >
          {isSubmitting ? 'Submitting...' : 'Create Search Request'}
        </button>
      </form>
    </div>
  );
};

export default FindTeeTimes;
