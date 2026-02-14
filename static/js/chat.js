// ==========================================
// Chat UI Functions
// ==========================================

const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const chatMessages = document.getElementById('chatMessages');

/**
 * Format bot message for display
 */
function formatBotMessage(text) {
    if (!text) return '';
    const lines = text.split('\n');
    let html = '';
    lines.forEach(line => {
        html += `<div style="margin: 4px 0;">${line}</div>`;
    });
    return html;
}

/**
 * Escape HTML special characters
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Scroll chat to bottom
 */
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Add a message to the chat
 */
function addMessage(text, isUser, icon = '', messageClass = '', fileAttachment = '') {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${isUser ? 'user' : 'bot'} ${messageClass}`;
    
    if (isUser) {
        msgDiv.innerHTML = `<div class="message-bubble user-bubble"><p>${escapeHtml(text)}</p>${fileAttachment}</div>`;
    } else {
        msgDiv.innerHTML = `
            ${icon ? `<span class="message-icon">${icon}</span>` : ''}
            <div class="message-bubble">${formatBotMessage(text)}</div>
        `;
    }
    
    // Show date label if it exists
    const dateLabel = document.querySelector('.current-date-label');
    if (dateLabel) {
        dateLabel.classList.add('has-content');
    }
    
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
}

/**
 * Add typing indicator
 */
function addTypingIndicator() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot';
    msgDiv.id = 'typingIndicator';
    msgDiv.innerHTML = `
        <div class="typing-indicator">
            <span></span><span></span><span></span>
        </div>
    `;
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
}

/**
 * Remove typing indicator
 */
function removeTypingIndicator() {
    const typing = document.getElementById('typingIndicator');
    if (typing) typing.remove();
}

/**
 * Add quick action buttons
 */
function addQuickActions(actions) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot';
    msgDiv.innerHTML = `
        <div class="quick-actions">
            ${actions.map(a => `<button class="quick-action-btn" onclick="sendQuickMessage('${a.replace(/'/g, "\\'")}')">${a}</button>`).join('')}
        </div>
    `;
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
}

/**
 * Add example messages
 */
function addExamples(examples) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot';
    msgDiv.innerHTML = `
        <div class="examples-section">
            ${examples.map(e => `<div style="padding: 4px 0; color: #8e8ea0;">• ${e}</div>`).join('')}
        </div>
    `;
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
}

/**
 * Send a quick message
 */
function sendQuickMessage(text) {
    chatInput.value = text;
    sendMessage();
}

// Export for use in other modules
window.formatBotMessage = formatBotMessage;
window.escapeHtml = escapeHtml;
window.scrollToBottom = scrollToBottom;
window.addMessage = addMessage;
window.addTypingIndicator = addTypingIndicator;
window.removeTypingIndicator = removeTypingIndicator;
window.addQuickActions = addQuickActions;
window.addExamples = addExamples;
window.sendQuickMessage = sendQuickMessage;
window.chatMessages = chatMessages;

// ==========================================
// Event Delegation for Dynamic Content
// ==========================================

/**
 * Handle event item clicks (update/delete) using event delegation
 */
document.addEventListener('click', function(e) {
    console.log('Click detected on:', e.target);
    
    // Find the closest event-item ancestor with data-event-url
    const eventItem = e.target.closest('.event-item[data-event-url]');
    
    if (!eventItem) {
        // Also try data-event-id for delete actions
        const eventItemDelete = e.target.closest('.event-item[data-event-id]');
        if (!eventItemDelete) return;
        
        const eventId = eventItemDelete.dataset.eventId;
        const action = eventItemDelete.dataset.action;
        
        if (!eventId || !action) return;
        
        console.log('Delete event clicked, eventId:', eventId);
        
        e.preventDefault();
        e.stopPropagation();
        
        if (action === 'delete') {
            handleDeleteSelection(eventId);
        }
        return;
    }
    
    const eventUrl = eventItem.dataset.eventUrl;
    const action = eventItem.dataset.action;
    
    console.log('Event item found, eventUrl:', eventUrl, 'action:', action);
    
    if (!eventUrl || !action) return;
    
    // Prevent default behavior and stop propagation
    e.preventDefault();
    e.stopPropagation();
    
    if (action === 'update') {
        handleUpdateSelection(eventUrl);
    } else if (action === 'delete') {
        // For delete, we still need the event ID
        const eventId = eventUrl.split('/update_event/')[1]?.split('?')[0];
        if (eventId) {
            handleDeleteSelection(eventId);
        }
    }
});

/**
 * Handle update event selection
 */
function handleUpdateSelection(eventUrl) {
    console.log('handleUpdateSelection called with URL:', eventUrl);
    
    // Get chatMessages safely
    const chatMessagesEl = document.getElementById('chatMessages');
    if (!chatMessagesEl) {
        console.error('chatMessages element not found');
        // Fallback to global variable
        if (typeof chatMessages === 'undefined') {
            alert('Error: Chat messages container not found');
            return;
        }
    }
    
    // Store the last user message before showing loading indicator
    const userMessages = (chatMessagesEl || chatMessages).querySelectorAll('.message.user');
    const lastUserMessage = userMessages.length > 0 
        ? userMessages[userMessages.length - 1].textContent.trim() 
        : 'Updated meeting';
    
    // Show loading indicator
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message bot';
    loadingDiv.innerHTML = '<span class="message-icon">🔄</span><div class="message-bubble">Updating meeting...</div>';
    (chatMessagesEl || chatMessages).appendChild(loadingDiv);
    
    // Scroll to bottom
    const scrollContainer = chatMessagesEl || chatMessages;
    scrollContainer.scrollTop = scrollContainer.scrollHeight;
    
    fetch(eventUrl, {
        method: 'GET',
        headers: {
            'Content-Type': 'text/html'
        }
    })
    .then(response => {
        if (response.redirected) {
            window.location.href = response.url;
            return;
        }
        return response.text();
    })
    .then(html => {
        if (html) {
            // Remove loading indicator
            loadingDiv.remove();
            
            // Store the HTML as-is for proper formatting
            const botMessage = html;
            
            // Insert the response HTML into chat
            (chatMessagesEl || chatMessages).insertAdjacentHTML('beforeend', html);
            
            // Scroll to bottom
            const scrollContainer = chatMessagesEl || chatMessages;
            scrollContainer.scrollTop = scrollContainer.scrollHeight;
            
            // Save update result to chat history with HTML for proper formatting
            const today = new Date().toISOString().split('T')[0];
            addToChatHistory(today, lastUserMessage, botMessage, 'success', '', true);
        }
    })
    .catch(error => {
        loadingDiv.remove();
        console.error('Error updating meeting:', error);
        addMessage('Error updating meeting: ' + error.message, false, '❌', 'error');
    });
}

/**
 * Handle delete event selection
 */
async function handleDeleteSelection(eventId) {
    // Store the last user message before showing loading indicator
    const userMessages = chatMessages.querySelectorAll('.message.user');
    const lastUserMessage = userMessages.length > 0 
        ? userMessages[userMessages.length - 1].textContent.trim() 
        : 'Cancelled meeting';
    
    // Show loading indicator
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message bot';
    loadingDiv.innerHTML = '<span class="message-icon">🗑️</span><div class="message-bubble">Cancelling meeting...</div>';
    chatMessages.appendChild(loadingDiv);
    scrollToBottom();
    
    try {
        const response = await fetch('/delete_event/' + eventId, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });
        
        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        
        loadingDiv.remove();
        
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            
            if (data.success) {
                // Render the full cancellation details
                const detailsHtml = renderCancellationDetails(data);
                chatMessages.insertAdjacentHTML('beforeend', detailsHtml);
                scrollToBottom();
                
                // Save to chat history with HTML for proper formatting
                const today = new Date().toISOString().split('T')[0];
                addToChatHistory(today, lastUserMessage, detailsHtml, 'success', '', true);
                
                // Redirect if specified
                if (data.redirect) {
                    setTimeout(() => {
                        window.location.href = data.redirect;
                    }, 2000);
                }
            } else {
                // Show error
                addMessage(data.message || 'Cancellation failed', false, '❌', 'error');
                
                if (data.redirect) {
                    setTimeout(() => {
                        window.location.href = data.redirect;
                    }, 1500);
                }
            }
        } else {
            // HTML response - extract and insert
            const html = await response.text();
            const messagesHtml = extractMessagesContent(html);
            chatMessages.insertAdjacentHTML('beforeend', messagesHtml);
            scrollToBottom();
            
            // Save to chat history with HTML
            const today = new Date().toISOString().split('T')[0];
            addToChatHistory(today, lastUserMessage, messagesHtml, 'success', '', true);
        }
    } catch (error) {
        loadingDiv.remove();
        console.error('Error cancelling meeting:', error);
        addMessage('Error cancelling meeting. Please try again.', false, '❌', 'error');
    }
}

/**
 * Render cancellation details from JSON response
 */
function renderCancellationDetails(data) {
    let detailsHtml = '';
    
    // Title and message
    detailsHtml += `<h3>${data.title || 'Meeting Cancelled'}</h3>`;
    detailsHtml += `<p>${data.message || 'Meeting has been cancelled successfully!'}</p>`;
    
    // Event details if available
    if (data.event_json || data.summary) {
        const event = data.event_json || {};
        const summary = data.summary || event.summary || '';
        const start = data.start || (event.start && event.start.dateTime ? new Date(event.start.dateTime).toLocaleString() : '');
        const end = data.end || (event.end && event.end.dateTime ? new Date(event.end.dateTime).toLocaleTimeString() : '');
        const location = data.location || event.location || '';
        const attendees = data.attendees || '';
        
        detailsHtml += '<div class="event-details">';
        
        if (summary) {
            detailsHtml += `<div class="detail-row"><span class="detail-label">Meeting:</span><span class="detail-value">${escapeHtml(summary)}</span></div>`;
        }
        
        if (start) {
            detailsHtml += `<div class="detail-row"><span class="detail-label">Date/Time:</span><span class="detail-value">${escapeHtml(start)}${end ? ' - ' + escapeHtml(end) : ''}</span></div>`;
        }
        
        if (location) {
            detailsHtml += `<div class="detail-row"><span class="detail-label">Location:</span><span class="detail-value">${escapeHtml(location)}</span></div>`;
        }
        
        if (attendees) {
            detailsHtml += `<div class="detail-row"><span class="detail-labe    l">Attendees:</span><span class="detail-value">${escapeHtml(attendees)}</span></div>`;
        }
        
        detailsHtml += '</div>';
    }
    
    // Quick actions
    detailsHtml += `<div class="quick-actions">
        <button class="quick-action-btn" onclick="window.location.href='/'">🏠 Create Another Meeting</button>
        <button class="quick-action-btn" onclick="window.location.href='/events'">📋 View All Events</button>
    </div>`;
    
    return `<div class="message bot success">
        <span class="message-icon">${data.icon || '🗑️'}</span>
        <div class="message-bubble">
            ${detailsHtml}
        </div>
    </div>`;
}

// Export event handler functions
window.handleUpdateSelection = handleUpdateSelection;
window.handleDeleteSelection = handleDeleteSelection;

