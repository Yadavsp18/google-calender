// ==========================================
// Events Page JavaScript
// Handles update and delete functionality for events page
// ==========================================

/**
 * Delete an event with confirmation
 */
async function deleteEvent(eventId, eventSummary) {
    if (!confirm(`Are you sure you want to delete "${eventSummary}"?`)) {
        return;
    }
    
    try {
        const response = await fetch('/delete_event/' + eventId, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Store message in session for display after redirect
            sessionStorage.setItem('last_action_message', JSON.stringify({
                type: 'success',
                title: 'Meeting Cancelled',
                icon: '🗑️',
                message: `Meeting '${eventSummary}' has been cancelled successfully!`
            }));
            sessionStorage.setItem('cancelled', 'true');
            
            // Redirect to home page
            window.location.href = '/';
        } else {
            alert(data.message || 'Failed to delete meeting');
        }
    } catch (error) {
        console.error('Error deleting event:', error);
        alert('Error deleting meeting. Please try again.');
    }
}

/**
 * Open update modal and load event details
 */
async function openUpdateModal(eventId) {
    const modal = document.getElementById('updateEventModal');
    const form = document.getElementById('updateEventForm');
    const submitBtn = document.getElementById('updateSubmitBtn');
    
    // Reset form
    form.reset();
    document.getElementById('updateEventId').value = eventId;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Loading...';
    
    try {
        const response = await fetch('/api/event/' + eventId);
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            return;
        }
        
        // Populate form with event details
        document.getElementById('updateSummary').value = data.summary || '';
        document.getElementById('updateLocation').value = data.location || '';
        document.getElementById('updateDescription').value = data.description || '';
        
        // Parse and set date/time from start_raw
        if (data.start_raw) {
            try {
                const startDate = new Date(data.start_raw);
                // Format: YYYY-MM-DD
                document.getElementById('updateDate').value = startDate.toISOString().split('T')[0];
                // Format: HH:MM
                const hours = String(startDate.getHours()).padStart(2, '0');
                const minutes = String(startDate.getMinutes()).padStart(2, '0');
                document.getElementById('updateTime').value = `${hours}:${minutes}`;
            } catch (e) {
                console.log('Could not parse event date:', e);
            }
        }
        
        submitBtn.disabled = false;
        submitBtn.textContent = 'Update Event';
        
        // Show modal
        modal.classList.add('active');
        
    } catch (error) {
        console.error('Error fetching event:', error);
        alert('Error loading event details. Please try again.');
    }
}

/**
 * Close update modal
 */
function closeUpdateModal() {
    const modal = document.getElementById('updateEventModal');
    modal.classList.remove('active');
}

/**
 * Handle update form submission
 */
async function submitUpdateForm(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    const submitBtn = document.getElementById('updateSubmitBtn');
    
    // Convert form data to JSON
    const data = {};
    formData.forEach((value, key) => {
        data[key] = value;
    });
    
    const eventId = data.eventId;
    delete data.eventId;
    
    submitBtn.disabled = true;
    submitBtn.textContent = 'Updating...';
    
    try {
        const response = await fetch('/api/event/' + eventId, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Close modal
            closeUpdateModal();
            
            // Store success message
            sessionStorage.setItem('last_action_message', JSON.stringify({
                type: 'success',
                title: 'Meeting Updated',
                icon: '✅',
                message: result.message
            }));
            
            // Reload events page
            window.location.href = '/';
        } else {
            alert(result.message || 'Failed to update meeting');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Update Event';
        }
        
    } catch (error) {
        console.error('Error updating event:', error);
        alert('Error updating meeting. Please try again.');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Update Event';
    }
}

/**
 * Initialize event handlers when DOM is ready
 */
document.addEventListener('DOMContentLoaded', function() {
    // Handle delete buttons
    document.querySelectorAll('.delete-event-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const eventId = this.dataset.eventId;
            const eventSummary = this.dataset.eventSummary;
            deleteEvent(eventId, eventSummary);
        });
    });
    
    // Handle update buttons
    document.querySelectorAll('.update-event-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const eventId = this.dataset.eventId;
            openUpdateModal(eventId);
        });
    });
    
    // Handle update form submission
    const updateForm = document.getElementById('updateEventForm');
    if (updateForm) {
        updateForm.addEventListener('submit', submitUpdateForm);
    }
    
    // Close modal when clicking outside
    const modal = document.getElementById('updateEventModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeUpdateModal();
            }
        });
        
        // Close modal on escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && modal.classList.contains('active')) {
                closeUpdateModal();
            }
        });
    }
    
    // Check for action messages from session storage
    const actionMessage = sessionStorage.getItem('last_action_message');
    const cancelled = sessionStorage.getItem('cancelled');
    
    if (actionMessage || cancelled) {
        // Clear from session storage
        sessionStorage.removeItem('last_action_message');
        sessionStorage.removeItem('cancelled');
        
        // Show message if exists
        if (actionMessage) {
            try {
                const messageData = JSON.parse(actionMessage);
                showActionMessage(messageData);
            } catch (e) {
                console.error('Error parsing action message:', e);
            }
        }
    }
});

/**
 * Show action message (success/error) on the page
 */
function showActionMessage(messageData) {
    const messagesContainer = document.getElementById('chatMessages');
    if (!messagesContainer) return;
    
    // Check if there's already a bot message
    const existingBotMessage = messagesContainer.querySelector('.message.bot');
    if (existingBotMessage) {
        // Update existing message instead of adding new one
        existingBotMessage.innerHTML = `
            <span class="message-icon">${messageData.icon || 'ℹ️'}</span>
            <div class="message-bubble">
                <h3>${escapeHtml(messageData.title)}</h3>
                <p>${escapeHtml(messageData.message)}</p>
            </div>
        `;
        return;
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message bot ${messageData.type || ''}`;
    messageDiv.innerHTML = `
        <span class="message-icon">${messageData.icon || 'ℹ️'}</span>
        <div class="message-bubble">
            <h3>${escapeHtml(messageData.title)}</h3>
            <p>${escapeHtml(messageData.message)}</p>
        </div>
    `;
    
    messagesContainer.insertBefore(messageDiv, messagesContainer.firstChild);
}

/**
 * Escape HTML special characters
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Export functions to global scope
window.deleteEvent = deleteEvent;
window.openUpdateModal = openUpdateModal;
window.closeUpdateModal = closeUpdateModal;
window.showActionMessage = showActionMessage;
window.escapeHtml = escapeHtml;
