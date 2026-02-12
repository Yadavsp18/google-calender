// ==========================================
// Google Drive Picker Functions
// ==========================================

const GOOGLE_CLIENT_ID = '926110940194-9mp8crham7ordce7rvs9rqm9rppgb82u.apps.googleusercontent.com';
const DEVELOPER_KEY = '{{ DEVELOPER_KEY }}';

/**
 * Open Google Drive picker
 */
function openGoogleDrivePicker() {
    fetch('/api/auth/token')
        .then(response => response.json())
        .then(data => {
            if (data.error || !data.access_token) {
                alert('Please log in first to use Google Drive picker.');
                return;
            }
            showGoogleDrivePicker(data.access_token);
        })
        .catch(error => console.error('Error fetching token:', error));
}

/**
 * Show Google Drive picker
 */
function showGoogleDrivePicker(accessToken) {
    if (typeof google !== 'undefined' && typeof google.picker !== 'undefined') {
        createPickerWithToken(accessToken);
    } else {
        loadGooglePickerAPI(accessToken);
    }
}

/**
 * Load Google Picker API
 */
function loadGooglePickerAPI(accessToken) {
    window.pendingPickerToken = accessToken;
    
    if (window.pickerAPILoading) return;
    window.pickerAPILoading = true;
    
    const script = document.createElement('script');
    script.src = 'https://apis.google.com/js/api.js';
    script.onload = function() {
        window.pickerAPILoading = false;
        gapi.load('picker', {
            callback: function() {
                if (window.pendingPickerToken) {
                    createPickerWithToken(window.pendingPickerToken);
                    window.pendingPickerToken = null;
                }
            }
        });
    };
    document.head.appendChild(script);
}

/**
 * Create Google Drive picker with token
 */
function createPickerWithToken(accessToken) {
    try {
        const picker = new google.picker.PickerBuilder()
            .addView(google.picker.ViewId.DOCS)
            .addView(google.picker.ViewId.DOCUMENTS)
            .addView(google.picker.ViewId.FOLDERS)
            .setOAuthToken(accessToken)
            .setDeveloperKey(DEVELOPER_KEY)
            .setCallback(pickerCallback)
            .build();
        picker.setVisible(true);
    } catch (e) {
        console.error('Error creating picker:', e);
        fallbackToUrlPrompt();
    }
}

/**
 * Google Drive picker callback
 */
function pickerCallback(data) {
    if (data.action === google.picker.Action.PICKED) {
        const doc = data.docs[0];
        const driveFile = {
            name: doc.name || 'Google Drive File',
            type: 'drive-link',
            content: doc.url || doc.webViewLink,
            fileId: doc.id
        };
        addFile(driveFile);
    }
}

/**
 * Fallback to URL prompt if picker fails
 */
function fallbackToUrlPrompt() {
    const driveUrl = prompt('Enter Google Drive file URL:');
    if (driveUrl && driveUrl.trim()) {
        addFile({
            name: 'Google Drive File',
            type: 'drive-link',
            content: driveUrl.trim()
        });
    }
}

// Export for use in other modules
window.GOOGLE_CLIENT_ID = GOOGLE_CLIENT_KEY;
window.DEVELOPER_KEY = DEVELOPER_KEY;
window.openGoogleDrivePicker = openGoogleDrivePicker;
window.showGoogleDrivePicker = showGoogleDrivePicker;
window.loadGooglePickerAPI = loadGooglePickerAPI;
window.createPickerWithToken = createPickerWithToken;
window.pickerCallback = pickerCallback;
window.fallbackToUrlPrompt = fallbackToUrlPrompt;
