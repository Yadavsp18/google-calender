// ==========================================
// Main Entry Point
// ==========================================

// Load all modules
console.log('Loading modules...');

// ==========================================
// Initialization
// ==========================================

// Run immediately when DOM is ready
async function initializeChat() {
    console.log('Initializing chat...');
    
    // Check if we're on the auth page (auth page has authPage element)
    const isAuthPageResult = isAuthPage();
    console.log('Is auth page:', isAuthPageResult);
    
    if (isAuthPageResult) {
        // On auth page, don't load anything - just return
        console.log('Auth page detected, skipping chat initialization');
        return;
    }
    
    console.log('Non-auth page, initializing chat features...');
    
    // Check for chat message from session
    const chatMessageEl = document.getElementById('chatMessageData');
    if (chatMessageEl && chatMessageEl.dataset.message) {
        try {
            const messageData = JSON.parse(chatMessageEl.dataset.message);
            
            // Handle action_message (cancelled/updated meeting details)
            if (messageData.show_details) {
                // Build details HTML
                let detailsHtml = '';
                if (messageData.summary) {
                    detailsHtml += `<div class="detail-row"><span class="detail-label">Meeting Title:</span><span class="detail-value">${escapeHtml(messageData.summary)}</span></div>`;
                }
                if (messageData.start) {
                    detailsHtml += `<div class="detail-row"><span class="detail-label">Start:</span><span class="detail-value">${escapeHtml(messageData.start)}</span></div>`;
                }
                if (messageData.end) {
                    detailsHtml += `<div class="detail-row"><span class="detail-label">End:</span><span class="detail-value">${escapeHtml(messageData.end)}</span></div>`;
                }
                if (messageData.location) {
                    detailsHtml += `<div class="detail-row"><span class="detail-label">Location:</span><span class="detail-value">${escapeHtml(messageData.location)}</span></div>`;
                }
                if (messageData.attendees) {
                    detailsHtml += `<div class="detail-row"><span class="detail-label">Attendees:</span><span class="detail-value">${escapeHtml(messageData.attendees)}</span></div>`;
                }
                if (messageData.description) {
                    detailsHtml += `<div class="detail-row"><span class="detail-label">Description:</span><span class="detail-value">${escapeHtml(messageData.description)}</span></div>`;
                }
                
                const msgDiv = document.createElement('div');
                msgDiv.className = `message bot ${messageData.message_type || ''}`;
                msgDiv.innerHTML = `
                    ${messageData.icon ? `<span class="message-icon">${messageData.icon}</span>` : ''}
                    <div class="message-bubble">
                        <h3>${escapeHtml(messageData.title)}</h3>
                        <p>${escapeHtml(messageData.content)}</p>
                        ${detailsHtml ? `<div class="event-details">${detailsHtml}</div>` : ''}
                    </div>
                `;
                chatMessages.appendChild(msgDiv);
                scrollToBottom();
            } else {
                // Regular message
                if (messageData.type === 'success') {
                    addMessage(messageData.message || 'Meeting processed successfully', false, messageData.icon || '✅', messageData.type);
                } else if (messageData.type === 'error') {
                    addMessage(messageData.message || 'An error occurred', false, messageData.icon || '❌', messageData.type);
                } else {
                    addMessage(messageData.message || 'Meeting processed', false, messageData.icon || 'ℹ️', messageData.type);
                }
            }
        } catch (e) {
            console.error('Error parsing chat message:', e);
        }
    }
    
    // Load sidebar with chat dates
    await loadChatDates();
    
    // Try to load today's chat history first
    const hasTodayChats = await renderTodayChatHistory();
    
    // If no chats for today, show welcome message
    if (!hasTodayChats) {
        showWelcomeMessage();
    }
    
    // Add Enter key listener
    if (chatInput) {
        chatInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
    
    // Add click listener for send button
    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }
    
    console.log('Initialization complete');
}

/**
 * Show welcome message when no chat history exists
 */
function showWelcomeMessage() {
    // Clear chat messages
    chatMessages.innerHTML = '';
    
    // Add date label
    const dateLabel = document.createElement('div');
    dateLabel.className = 'current-date-label';
    dateLabel.textContent = "Today's Chats";
    chatMessages.appendChild(dateLabel);
    
    // Show welcome message with examples
    const helpMsg = 'Hi! I can help you manage your Google Calendar. Try saying:';
    const examples = [
        "Create a meeting with John tomorrow at 3pm",
        "Show my events for next week",
        "Cancel my 2pm meeting",
        "Reschedule Friday's meeting to 4pm"
    ];
    addQuickActions(['Create Meeting', 'View Events', 'List Events']);
    addExamples(examples);
}

// Run on DOMContentLoaded (fires as soon as DOM is ready - faster)
document.addEventListener('DOMContentLoaded', initializeChat);

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('addFileDropdown');
    const btn = document.querySelector('.add-icon');
    if (!dropdown.contains(event.target) && !btn.contains(event.target)) {
        dropdown.classList.remove('show');
    }
});

console.log('All modules loaded');
