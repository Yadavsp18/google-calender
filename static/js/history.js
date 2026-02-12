// ==========================================
// Chat History Functions (JSON File Storage)
// ==========================================

/**
 * Get all chat dates from the server
 */
async function getAllChatDates() {
    try {
        const response = await fetch('/api/chats');
        const data = await response.json();
        if (data.success) {
            return data.dates || [];
        }
        return [];
    } catch (error) {
        console.error('Error fetching chat dates:', error);
        return [];
    }
}

/**
 * Get chat history for a specific date from the server
 */
async function getChatHistoryForDate(date) {
    try {
        const response = await fetch(`/api/chats/${date}`);
        const data = await response.json();
        if (data.success) {
            return data.chats || [];
        }
        return [];
    } catch (error) {
        console.error('Error fetching chat history:', error);
        return [];
    }
}

/**
 * Save chat history for a specific date to the server
 */
async function saveChatHistoryForDate(date, chats) {
    try {
        // For now, we only append new chats, not overwrite
        // The server will handle appending new messages
    } catch (error) {
        console.error('Error saving chat history:', error);
    }
}

/**
 * Add a chat entry to history on the server
 */
async function addToChatHistory(date, userMessage, botMessage, messageType = 'info', fileAttachment = '', updateLast = false) {
    try {
        const response = await fetch('/api/chats', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                date: date,
                userMessage: userMessage,
                botMessage: botMessage,
                messageType: messageType,
                fileAttachment: fileAttachment
            })
        });
        const data = await response.json();
        if (!data.success) {
            console.error('Failed to save chat:', data.error);
        }
    } catch (error) {
        console.error('Error saving chat to server:', error);
    }
}

/**
 * Clear all chat history on the server
 */
async function clearChatHistory() {
    try {
        const response = await fetch('/api/chats', {
            method: 'DELETE'
        });
        const data = await response.json();
        if (!data.success) {
            console.error('Failed to clear chats:', data.error);
        }
    } catch (error) {
        console.error('Error clearing chats:', error);
    }
}

// Export for use in other modules
window.getAllChatDates = getAllChatDates;
window.getChatHistoryForDate = getChatHistoryForDate;
window.saveChatHistoryForDate = saveChatHistoryForDate;
window.addToChatHistory = addToChatHistory;
window.clearChatHistory = clearChatHistory;
