// ==========================================
// Authentication Functions
// ==========================================

/**
 * Check if user is on auth page by looking for auth-specific element
 */
function isAuthPage() {
    return !!document.getElementById('authPage');
}

/**
 * Check if user is authenticated by calling the API
 */
async function checkAuthentication() {
    try {
        const response = await fetch('/api/auth/check');
        const data = await response.json();
        return data.authenticated === true;
    } catch (e) {
        console.error('Auth check failed:', e);
        return false;
    }
}

/**
 * Redirect to main page if authenticated
 */
async function redirectIfAuthenticated() {
    const isAuth = await checkAuthentication();
    if (isAuth && isAuthPage()) {
        console.log('User is authenticated, redirecting to /');
        window.location.href = '/';
    }
}

/**
 * Logout user and redirect to auth page
 */
function logout() {
    if (confirm('Are you sure you want to logout?')) {
        fetch('/logout', { 
            method: 'POST',
            credentials: 'same-origin'
        })
        .then(response => {
            window.location.href = '/auth';
        })
        .catch(() => {
            window.location.href = '/auth';
        });
    }
}

// Export for use in other modules
window.isAuthPage = isAuthPage;
window.checkAuthentication = checkAuthentication;
window.redirectIfAuthenticated = redirectIfAuthenticated;
window.logout = logout;
