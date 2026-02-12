// ==========================================
// File Attachment Functions
// ==========================================

/**
 * Toggle add file dropdown
 */
function toggleAddFileDropdown() {
    const dropdown = document.getElementById('addFileDropdown');
    dropdown.classList.toggle('show');
}

/**
 * Select file source (system files or Google Drive)
 */
function selectFileSource(source) {
    const dropdown = document.getElementById('addFileDropdown');
    dropdown.classList.remove('show');
    
    if (source === 'system files') {
        const fileInput = document.getElementById('systemFileInput');
        if (fileInput) {
            fileInput.click();
        } else {
            const input = document.createElement('input');
            input.type = 'file';
            input.id = 'systemFileInput';
            input.style.display = 'none';
            document.body.appendChild(input);
            input.click();
            
            input.addEventListener('change', function(e) {
                if (this.files.length > 0) {
                    addFile(this.files[0]);
                }
            });
        }
    } else if (source === 'google drive') {
        openGoogleDrivePicker();
    }
}

/**
 * Add a file attachment
 */
function addFile(file) {
    const chatContainer = document.querySelector('.chat-input-container');
    if (!chatContainer) return;
    
    if (file.type === 'drive-link') {
        const fileDiv = document.createElement('div');
        fileDiv.className = 'file-attachment';
        fileDiv.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
            </svg>
            <span>${escapeHtml(file.name)}</span>
            <a href="${escapeHtml(file.content)}" target="_blank" style="margin-left: 8px; color: #10a37f;">Open</a>
        `;
        chatContainer.insertBefore(fileDiv, chatInput);
        window.pendingFile = file;
    } else {
        const reader = new FileReader();
        reader.onload = function(e) {
            const fileDiv = document.createElement('div');
            fileDiv.className = 'file-attachment';
            fileDiv.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
                <span>${escapeHtml(file.name)}</span>
                <span style="margin-left: 8px; color: #8e8ea0;">(${(file.size / 1024).toFixed(1)} KB)</span>
            `;
            chatContainer.insertBefore(fileDiv, chatInput);
            window.pendingFile = { name: file.name, type: file.type, content: e.target.result };
        };
        reader.readAsDataURL(file);
    }
}

// Export for use in other modules
window.toggleAddFileDropdown = toggleAddFileDropdown;
window.selectFileSource = selectFileSource;
window.addFile = addFile;
