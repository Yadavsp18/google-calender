// ==========================================
// Send Message Functions
// ==========================================

/**
 * Extract messages content from full HTML page response
 */
function extractMessagesContent(html) {
    if (!html) return '';
    
    // Check if it's a full HTML page (contains DOCTYPE or <html tag)
    const isFullPage = /<!DOCTYPE|<html\s/i.test(html);
    
    if (!isFullPage) {
        // Already a fragment, return as-is
        return html;
    }
    
    // Extract content between the messages block tags
    const messagesMatch = html.match(/<div\s+class=["']chat-messages["'][^>]*>([\s\S]*?)<\/div\s*>/i);
    if (messagesMatch && messagesMatch[1]) {
        return messagesMatch[1];
    }
    
    // Try to find any message divs
    const messageDivsMatch = html.match(/<div\s+class=["'][[^"]^"]*message*["'][^>]*>([\s\S]*?)<\/div\s*>/gi);
    if (messageDivsMatch) {
        return messageDivsMatch.join('');
    }
    
    // Fallback: return empty string
    return '';
}

/**
 * Render event selection UI from JSON response
 */
function renderEventSelection(data) {
    if (!data.events || data.events.length === 0) {
        return `
            <div class="message bot">
                <span class="message-icon">${data.icon || 'ℹ️'}</span>
                <div class="message-bubble">
                    <h3>${data.title || 'Info'}</h3>
                    <p>${data.message || 'No events found'}</p>
                </div>
            </div>
        `;
    }
    
    const eventsHtml = data.events.map((event, index) => `
        <div class="event-item" data-event-id="${event.id}" data-action="delete">
            <div class="event-summary">${escapeHtml(event.summary)}</div>
            <div class="event-time">${escapeHtml(event.start)} - ${escapeHtml(event.end)}</div>
            ${event.location ? `<div class="event-location">${escapeHtml(event.location)}</div>` : ''}
            ${event.attendees ? `<div class="event-attendees">👥 ${escapeHtml(event.attendees)}</div>` : ''}
        </div>
    `).join('');
    
    return `
        <div class="message bot">
            <span class="message-icon">${data.icon || 'ℹ️'}</span>
            <div class="message-bubble">
                <h3>${data.title || 'Select Event'}</h3>
                <p>${data.message || 'Please select an event:'}</p>
                <div class="events-list">
                    ${eventsHtml}
                </div>
            </div>
        </div>
    `;
}

/**
 * Render JSON response as HTML
 */
function renderJsonResponse(data) {
    // Check if it's a selection UI response
    if (data.show_selection && data.events) {
        return renderEventSelection(data);
    }
    
    // Check for other JSON response types
    if (data.title || data.message) {
        return `
            <div class="message bot ${data.message_type || ''}">
                ${data.icon ? `<span class="message-icon">${data.icon}</span>` : ''}
                <div class="message-bubble">
                    <h3>${data.title || 'Info'}</h3>
                    <p>${data.message || ''}</p>
                    ${data.show_details ? renderEventDetails(data) : ''}
                </div>
            </div>
        `;
    }
    
    // Fallback - return empty
    return '';
}

/**
 * Render event details from JSON data
 */
function renderEventDetails(data) {
    let detailsHtml = '';
    
    if (data.summary) {
        detailsHtml += `<div class="detail-row"><span class="detail-label">Meeting Title:</span><span class="detail-value">${escapeHtml(data.summary)}</span></div>`;
    }
    if (data.start) {
        detailsHtml += `<div class="detail-row"><span class="detail-label">Start:</span><span class="detail-value">${escapeHtml(data.start)}</span></div>`;
    }
    if (data.end) {
        detailsHtml += `<div class="detail-row"><span class="detail-label">End:</span><span class="detail-value">${escapeHtml(data.end)}</span></div>`;
    }
    if (data.location) {
        detailsHtml += `<div class="detail-row"><span class="detail-label">Location:</span><span class="detail-value">${escapeHtml(data.location)}</span></div>`;
    }
    if (data.attendees) {
        detailsHtml += `<div class="detail-row"><span class="detail-label">Attendees:</span><span class="detail-value">${escapeHtml(data.attendees)}</span></div>`;
    }
    
    return `<div class="event-details">${detailsHtml}</div>`;
}

/**
 * Send message to the server
 */
async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text && !window.pendingFile) return;
    
    // Mark that we have messages to send
    hasUnsavedMessages = true;
    
    let messageText = text;
    let fileAttachment = '';
    if (window.pendingFile) {
        fileAttachment = `<div class="file-attachment sent-file">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
            <span>${escapeHtml(window.pendingFile.name)}</span>
        </div>`;
        const fileDiv = document.querySelector('.file-attachment:not(.sent-file)');
        if (fileDiv) fileDiv.remove();
    }
    
    addMessage(messageText, true, '', '', fileAttachment);
    chatInput.value = '';
    sendBtn.disabled = true;
    
    // Save user message to chat history immediately (before server response)
    const today = new Date().toISOString().split('T')[0];
    addToChatHistory(today, text, '', 'pending', fileAttachment);
    
    addTypingIndicator();
    
    try {
        const formData = new FormData();
        formData.append('sentence', text);
            
            if (window.pendingFile && window.pendingFile.type === 'drive-link' && window.pendingFile.fileId) {
                try {
                    const fileInfoResponse = await fetch('/api/drive/file-info', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ fileId: window.pendingFile.fileId })
                    });
                    const fileInfoData = await fileInfoResponse.json();
                    if (fileInfoData.success) {
                        formData.append('drive_file_id', fileInfoData.file.id);
                        formData.append('drive_file_name', fileInfoData.file.name);
                        formData.append('drive_file_url', fileInfoData.file.webViewLink);
                    }
                } catch (e) {
                    console.error('Error getting Drive file info:', e);
                }
            }
            
            if (window.pendingFile && window.pendingFile.type !== 'drive-link') {
                formData.append('file_name', window.pendingFile.name);
                formData.append('file_content', window.pendingFile.content);
                if (window.pendingFile.type) {
                    formData.append('file_type', window.pendingFile.type);
                }
            }
            
            removeTypingIndicator();
            
            const response = await fetch('/nlp_create', {
                method: 'POST',
                body: formData
            });
            
            // Check content type to determine response format
            const contentType = response.headers.get('content-type');
            let messagesHtml = '';
            let botResponseData = null;
            
            if (contentType && contentType.includes('application/json')) {
                // Response is JSON - render it as HTML
                botResponseData = await response.json();
                messagesHtml = renderJsonResponse(botResponseData);
            } else {
                // Response is HTML
                const data = await response.text();
                
                if (response.redirected) {
                    window.location.href = response.url;
                    return;
                }
                
                // Extract messages content from the response
                messagesHtml = extractMessagesContent(data);
            }
            
            // Append the response to chat
            chatMessages.insertAdjacentHTML('beforeend', messagesHtml);
            
            // Scroll to bottom
            scrollToBottom();
            
            // Save bot response to chat history using the messagesHtml directly
            // This ensures we save the correct response for this message
            addToChatHistory(today, text, messagesHtml, 'success', fileAttachment, true);
            
            const newChatInput = document.getElementById('chatInput');
            if (newChatInput) {
                newChatInput.focus();
            }
            
            const newSendBtn = document.getElementById('sendBtn');
            if (newSendBtn) {
                newSendBtn.disabled = false;
            }
            
            window.pendingFile = null;
            
            // Reset unsaved messages flag since message was saved
            hasUnsavedMessages = false;
            
            return;

        } catch (error) {
            removeTypingIndicator();
            addMessage('Error sending message: ' + error.message, false, '❌', 'error');
            sendBtn.disabled = false;
            
            // Reset unsaved messages flag even on error
            hasUnsavedMessages = false;
        }
}

// Export for use in other modules
window.sendMessage = sendMessage;
window.renderJsonResponse = renderJsonResponse;
window.renderEventSelection = renderEventSelection;

// ==========================================
// Auto Refresh Functions
// ==========================================

/**
 * Schedule auto-refresh after conversation
 */
function scheduleAutoRefresh() {
    // Refresh after 3 seconds
    setTimeout(() => {
        window.location.reload();
    }, 3000);
}

/**
 * Auto-refresh page
 */
function refreshPage() {
    window.location.reload();
}

window.scheduleAutoRefresh = scheduleAutoRefresh;
window.refreshPage = refreshPage;
