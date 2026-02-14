// ==========================================
// Calendar View Functions
// ==========================================

let isCalendarView = false;
let calendarEmbedUrl = '';

/**
 * Toggle calendar view
 */
async function toggleCalendarView() {
    if (isCalendarView) {
        hideCalendarView();
    } else {
        await showCalendarView();
    }
}

/**
 * Show calendar view
 */
async function showCalendarView() {
    console.log('Loading Google Calendar...');
    isCalendarView = true;
    
    // Update button text
    const btn = document.getElementById('viewEventsBtn');
    if (btn) {
        btn.innerHTML = '📅 Hide Events';
    }
    
    // Check authentication
    try {
        const response = await fetch('/api/auth/check');
        const data = await response.json();
        
        if (!data.authenticated) {
            addMessage('Please connect your Google Calendar first.', false, '🔐', 'warning');
            isCalendarView = false;
            if (btn) btn.innerHTML = '📅 View Events';
            return;
        }
    } catch (error) {
        console.error('Auth check error:', error);
        isCalendarView = false;
        if (btn) btn.innerHTML = '📅 View Events';
        return;
    }
    
    // Fetch user email
    let userEmail = '';
    try {
        const eventsResponse = await fetch('/api/calendar/events');
        const eventsData = await eventsResponse.json();
        userEmail = eventsData.user_email || '';
    } catch (e) {
        console.log('Could not fetch user email');
    }
    
    // Build calendar embed URL
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    calendarEmbedUrl = userEmail 
        ? `https://calendar.google.com/calendar/embed?src=${encodeURIComponent(userEmail)}&ctz=${encodeURIComponent(timezone)}`
        : `https://calendar.google.com/calendar/embed?ctz=${encodeURIComponent(timezone)}`;
    
    // Log the calendar link for debugging
    console.log('Google Calendar Link:', calendarEmbedUrl);
    
    // Replace chat messages with calendar iframe
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = `
        <div class="calendar-embed">
            <iframe 
                src="${calendarEmbedUrl}"
                style="border: 0; width: 100%; height: 100%; display: block;"
                frameborder="0"
                scrolling="no">
            </iframe>
        </div>
    `;
}

/**
 * Hide calendar view
 */
function hideCalendarView() {
    isCalendarView = false;
    calendarEmbedUrl = '';
    
    // Update button text
    const btn = document.getElementById('viewEventsBtn');
    if (btn) {
        btn.innerHTML = '📅 View Events';
    }
    
    // Restore chat history or show welcome message
    renderTodayChatHistory().then(hasChats => {
        if (!hasChats) {
            showWelcomeMessage();
        }
    });
}

// Export for use in other modules
window.isCalendarView = isCalendarView;
window.calendarEmbedUrl = calendarEmbedUrl;
window.toggleCalendarView = toggleCalendarView;
window.showCalendarView = showCalendarView;
window.hideCalendarView = hideCalendarView;
