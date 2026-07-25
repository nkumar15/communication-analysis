/**
 * Format a date string or Date object to a localized date and time string.
 * Uses the user's browser locale and time zone.
 * 
 * @param {string|Date} date - The date to format (ISO string or Date object)
 * @param {object} options - Intl.DateTimeFormat options (optional)
 * @returns {string} Formatted date time string
 */
export const formatDateTime = (date, options = {}) => {
    if (!date) return 'N/A';

    const dateObj = new Date(date);

    // Default options: "Oct 27, 2023, 10:00 AM"
    const defaultOptions = {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: 'numeric',
        ...options
    };

    return new Intl.DateTimeFormat(undefined, defaultOptions).format(dateObj);
};

/**
 * Format a date string or Date object to a localized date string (no time).
 * 
 * @param {string|Date} date - The date to format
 * @returns {string} Formatted date string
 */
export const formatDate = (date) => {
    return formatDateTime(date, {
        hour: undefined,
        minute: undefined
    });
};
