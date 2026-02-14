// ==========================================
// Sidebar Functions
// ==========================================

/**
 * Track whether chat has been initialized
 */
let chatInitialized = false;

/**
 * Track if we're currently in a chat session with unsaved messages
 */
let hasUnsavedMessages = false;

/**
 * Escape HTML special characters
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Toggle sidebar collapse/expand
 */
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const expandBtn = document.getElementById('expandSidebarBtn');
    const mainWrapper = document.querySelector('.main-wrapper');
    
    if (sidebar.classList.contains('collapsed')) {
        // Expand sidebar
        sidebar.classList.remove('collapsed');
        expandBtn.style.display = 'none';
        if (mainWrapper) {
            mainWrapper.classList.remove('sidebar-collapsed');
        }
        // Re-initialize chat if it was initialized before
        // Only re-render if we don't have unsaved messages
        if (chatInitialized && typeof renderTodayChatHistory === 'function' && !hasUnsavedMessages) {
            renderTodayChatHistory();
        }
    } else {
        // Collapse sidebar
        sidebar.classList.add('collapsed');
        expandBtn.style.display = 'flex';
        if (mainWrapper) {
            mainWrapper.classList.add('sidebar-collapsed');
        }
    }
}

/**
 * Clear all chat history from server
 */
async function clearAllChatHistory() {
    try {
        await clearChatHistory();
        // Reload the page to refresh
        window.location.reload();
    } catch (error) {
        console.error('Error clearing chat history:', error);
        alert('Failed to clear chat history');
    }
}

/**
 * Load chat dates into sidebar from server
 */
async function loadChatDates() {
    // Check if we're on the events page - don't load sidebar chat dates there
    if (window.location.pathname === '/events') {
        console.log('Events page detected, skipping sidebar chat date loading');
        return;
    }
    
    try {
        const dates = await getAllChatDates();
        const datesList = document.getElementById('chatDatesList');
        
        if (dates.length === 0) {
            datesList.innerHTML = '<div class="no-history">No chat history</div>';
            return;
        }
        
        // Sort dates in descending order (newest first)
        dates.sort((a, b) => b.localeCompare(a));
        
        // Helper function to format date string properly (YYYY-MM-DD)
        const formatDateString = (dateStr) => {
            // Split the date string to avoid timezone issues
            const parts = dateStr.split('-');
            if (parts.length === 3) {
                const year = parseInt(parts[0]);
                const month = parseInt(parts[1]) - 1; // JS months are 0-indexed
                const day = parseInt(parts[2]);
                // Create date at noon local time to avoid timezone shifts
                const dateObj = new Date(year, month, day, 12, 0, 0);
                return dateObj.toLocaleDateString('en-US', { 
                    weekday: 'short', 
                    month: 'short', 
                    day: 'numeric' 
                });
            }
            // Fallback to original behavior
            const dateObj = new Date(date);
            return dateObj.toLocaleDateString('en-US', { 
                weekday: 'short', 
                month: 'short', 
                day: 'numeric' 
            });
        };
        
        datesList.innerHTML = dates.map(date => {
            const displayDate = formatDateString(date);
            return `<div class="date-item" data-date="${date}" onclick="loadChatsForDate('${date}')">${displayDate}</div>`;
        }).join('');
    } catch (error) {
        console.error('Error loading chat dates:', error);
        const datesList = document.getElementById('chatDatesList');
        datesList.innerHTML = '<div class="no-history">Failed to load history</div>';
    }
}

/**
 * Load chats for a specific date from server
 */
async function loadChatsForDate(date) {
    try {
        // Update active state in sidebar
        document.querySelectorAll('.date-item').forEach(item => item.classList.remove('active'));
        const dateItem = document.querySelector(`.date-item[data-date="${date}"]`);
        if (dateItem) dateItem.classList.add('active');
        
        // Load chat history from server
        const chats = await getChatHistoryForDate(date);
        
        // Clear chat messages
        chatMessages.innerHTML = '';
        
        // Add date label
        const dateLabel = document.createElement('div');
        dateLabel.className = 'current-date-label';
        // Parse date parts manually to avoid timezone issues
        const parts = date.split('-');
        let displayDate;
        if (parts.length === 3) {
            const year = parseInt(parts[0]);
            const month = parseInt(parts[1]) - 1;
            const day = parseInt(parts[2]);
            const dateObj = new Date(year, month, day, 12, 0, 0);
            displayDate = dateObj.toLocaleDateString('en-US', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            });
        } else {
            displayDate = new Date(date).toLocaleDateString('en-US', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            });
        }
        dateLabel.textContent = displayDate;
        chatMessages.appendChild(dateLabel);
        
        if (chats.length === 0) {
            chatMessages.appendChild(document.createElement('div')).className = 'no-history';
            chatMessages.querySelector('.no-history').textContent = 'No chats for this date';
        } else {
            // Render each chat message
            chats.forEach(chat => {
                const isUser = chat.messageType === 'user' || chat.messageType === 'pending';
                addMessage(chat.userMessage, isUser, '', '', chat.fileAttachment || '');
                
                if (chat.botMessage) {
                    // Add bot response if it exists
                    const msgDiv = document.createElement('div');
                    msgDiv.className = 'message bot';
                    msgDiv.innerHTML = chat.botMessage;
                    chatMessages.appendChild(msgDiv);
                }
            });
        }
        
        scrollToBottom();
    } catch (error) {
        console.error('Error loading chats for date:', error);
    }
}

/**
 * Render chat history for today's date
 */
async function renderTodayChatHistory() {
    try {
        const today = new Date().toISOString().split('T')[0];
        const chats = await getChatHistoryForDate(today);
        
        if (chats.length === 0) {
            return false; // No chats for today
        }
        
        // Clear chat messages first
        chatMessages.innerHTML = '';
        
        // Add date label
        const dateLabel = document.createElement('div');
        dateLabel.className = 'current-date-label';
        dateLabel.textContent = "Today's Chats";
        chatMessages.appendChild(dateLabel);
        
        // Render each chat message
        chats.forEach(chat => {
            const isUser = chat.messageType === 'user' || chat.messageType === 'pending';
            addMessage(chat.userMessage, isUser, '', '', chat.fileAttachment || '');
            
            if (chat.botMessage) {
                // Add bot response if it exists
                const msgDiv = document.createElement('div');
                msgDiv.className = 'message bot';
                // Check if it contains HTML tags, if so render as HTML
                if (/<[a-z][\s\S]*>/i.test(chat.botMessage)) {
                    msgDiv.innerHTML = chat.botMessage;
                } else {
                    // Render plain text
                    const lines = chat.botMessage.split('\n');
                    let html = '';
                    lines.forEach(line => {
                        html += `<div style="margin: 4px 0;">${escapeHtml(line)}</div>`;
                    });
                    msgDiv.innerHTML = html;
                }
                chatMessages.appendChild(msgDiv);
            }
        });
        
        scrollToBottom();
        return true;
    } catch (error) {
        console.error('Error rendering today chat history:', error);
        return false;
    } finally {
        // Mark chat as initialized after rendering
        chatInitialized = true;
    }
}

// Export for use in other modules
window.toggleSidebar = toggleSidebar;
window.clearAllChatHistory = clearAllChatHistory;
window.loadChatDates = loadChatDates;
window.loadChatsForDate = loadChatsForDate;
window.renderTodayChatHistory = renderTodayChatHistory;
