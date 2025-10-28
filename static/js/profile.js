/**
 * Profile page client-side functionality
 */

// Get CSRF token
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

// Show alert message
function showAlert(message, type = 'success') {
    const alertContainer = document.getElementById('alert-container');
    const alertClass = type === 'success'
        ? 'bg-green-50 border-green-200 text-green-800'
        : 'bg-red-50 border-red-200 text-red-800';

    const alert = document.createElement('div');
    alert.className = `${alertClass} border rounded-lg p-4 mb-4`;
    alert.innerHTML = `
        <div class="flex items-center justify-between">
            <p class="text-sm font-medium">${message}</p>
            <button onclick="this.parentElement.parentElement.remove()" class="text-gray-500 hover:text-gray-700">
                <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/>
                </svg>
            </button>
        </div>
    `;

    alertContainer.innerHTML = '';
    alertContainer.appendChild(alert);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

// Edit Profile Functionality
document.getElementById('edit-profile-btn')?.addEventListener('click', function() {
    document.getElementById('display-full-name').classList.add('hidden');
    document.getElementById('edit-full-name').classList.remove('hidden');
    document.getElementById('save-profile-container').classList.remove('hidden');
    this.classList.add('hidden');
});

document.getElementById('cancel-edit-btn')?.addEventListener('click', function() {
    document.getElementById('display-full-name').classList.remove('hidden');
    document.getElementById('edit-full-name').classList.add('hidden');
    document.getElementById('save-profile-container').classList.add('hidden');
    document.getElementById('edit-profile-btn').classList.remove('hidden');
});

document.getElementById('save-profile-btn')?.addEventListener('click', async function() {
    const fullName = document.getElementById('edit-full-name').value.trim();

    if (!fullName) {
        showAlert('Full name is required', 'error');
        return;
    }

    try {
        const response = await fetch('/profile/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ full_name: fullName })
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('display-full-name').textContent = fullName;
            document.getElementById('display-full-name').classList.remove('hidden');
            document.getElementById('edit-full-name').classList.add('hidden');
            document.getElementById('save-profile-container').classList.add('hidden');
            document.getElementById('edit-profile-btn').classList.remove('hidden');
            showAlert(data.message, 'success');
        } else {
            showAlert(data.message, 'error');
        }
    } catch (error) {
        console.error('Error updating profile:', error);
        showAlert('An error occurred while updating your profile', 'error');
    }
});

// Change Password Functionality
document.getElementById('change-password-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();

    const currentPassword = document.getElementById('current-password').value;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;

    // Client-side validation
    if (newPassword.length < 8) {
        showAlert('Password must be at least 8 characters long', 'error');
        return;
    }

    if (newPassword !== confirmPassword) {
        showAlert('New passwords do not match', 'error');
        return;
    }

    try {
        const response = await fetch('/profile/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword,
                confirm_password: confirmPassword
            })
        });

        const data = await response.json();

        if (data.success) {
            showAlert(data.message, 'success');
            // Reset form
            document.getElementById('change-password-form').reset();
        } else {
            showAlert(data.message, 'error');
        }
    } catch (error) {
        console.error('Error changing password:', error);
        showAlert('An error occurred while changing your password', 'error');
    }
});

// Export Data Functionality
document.getElementById('export-data-btn')?.addEventListener('click', async function() {
    try {
        const response = await fetch('/profile/export-data', {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });

        const result = await response.json();

        if (result.success) {
            // Create a downloadable JSON file
            const dataStr = JSON.stringify(result.data, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `solar-intelligence-data-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);

            showAlert('Your data has been downloaded successfully', 'success');
        } else {
            showAlert(result.message, 'error');
        }
    } catch (error) {
        console.error('Error exporting data:', error);
        showAlert('An error occurred while exporting your data', 'error');
    }
});

// Upgrade Plan Functionality
document.getElementById('upgrade-plan-btn')?.addEventListener('click', function() {
    // Redirect to Becquerel Institute shop page for SolarIntelligence.ai subscription
    window.location.href = 'https://www.becquerelinstitute.eu/shop/solarintelligence-ai-monthly-subscription-launch-offer-65';
});

// Refresh usage stats periodically (every 30 seconds)
setInterval(async function() {
    try {
        const response = await fetch('/profile/usage-stats');
        const data = await response.json();

        if (data.success) {
            // Update usage statistics on the page
            const stats = data.stats;
            // You can update specific elements here if needed
            console.log('Usage stats refreshed:', stats);
        }
    } catch (error) {
        console.error('Error refreshing stats:', error);
    }
}, 30000); // 30 seconds
