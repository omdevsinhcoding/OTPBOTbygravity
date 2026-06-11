/**
 * OTP Hub — Verification Flow
 * 
 * Flow:
 * 1. User clicks "Allow Check & Proceed"
 * 2. Location permission requested (loops until granted)
 * 3. reCAPTCHA v2 rendered and solved
 * 4. All data POSTed to VPS backend for validation
 * 5. Backend verifies reCAPTCHA with Google + stores data in Neon DB
 */

// ── Configuration ──
// ⚠️ IMPORTANT: Set this to your VPS IP/domain where the bot runs.
// Example: "http://161.118.182.184:8080" or "https://api.yourdomain.com"
const API_BASE = "https://161.118.182.184:8080";

// Extract token from URL
const urlParams = new URLSearchParams(window.location.search);
const TOKEN = urlParams.get('token');

let userLocation = null;
let recaptchaToken = null;
let recaptchaSiteKey = null;
let recaptchaWidgetId = null;

// ── Step references ──
const stepLocation = document.getElementById('step-location');
const stepCaptcha = document.getElementById('step-captcha');
const stepProcessing = document.getElementById('step-processing');
const stepSuccess = document.getElementById('step-success');
const stepError = document.getElementById('step-error');

// ── Initialize ──
document.addEventListener('DOMContentLoaded', async () => {
    if (!TOKEN) {
        showError('Invalid verification link. Please use the link from the Telegram bot.');
        return;
    }

    // Fetch session info (includes reCAPTCHA site key)
    try {
        const resp = await fetch(`${API_BASE}/api/session?token=${TOKEN}`);
        const data = await resp.json();

        if (data.error) {
            if (data.status === 'passed') {
                showSuccess();
            } else {
                showError(data.error);
            }
            return;
        }

        recaptchaSiteKey = data.recaptcha_site_key;
    } catch (err) {
        showError('Cannot connect to verification server. Please try again later.');
    }
});


/**
 * Step 1: Request location permission
 * Keeps asking until user grants it.
 */
function requestLocation() {
    const btn = document.getElementById('btn-location');
    const statusBox = document.getElementById('location-status');
    const statusText = document.getElementById('location-status-text');

    btn.disabled = true;
    btn.innerHTML = '<span class="btn-icon">⏳</span> Requesting Permission...';

    if (!navigator.geolocation) {
        showLocationError('Your browser does not support location. Please use a modern browser.');
        btn.disabled = false;
        btn.innerHTML = '<span class="btn-icon">📍</span> Allow Check & Proceed';
        return;
    }

    navigator.geolocation.getCurrentPosition(
        // ✅ Success
        (position) => {
            userLocation = {
                lat: position.coords.latitude,
                lng: position.coords.longitude,
                accuracy: position.coords.accuracy,
            };

            // Hide status, transition to step 2
            statusBox.classList.add('hidden');

            setTimeout(() => {
                showStep(stepCaptcha);
                renderRecaptcha();
            }, 500);
        },
        // ❌ Error (denied, unavailable, timeout)
        (error) => {
            let msg = '';
            switch (error.code) {
                case error.PERMISSION_DENIED:
                    msg = 'Location permission denied. Please tap the button again and select "Allow" to proceed.';
                    break;
                case error.POSITION_UNAVAILABLE:
                    msg = 'Location unavailable. Please enable GPS and try again.';
                    break;
                case error.TIMEOUT:
                    msg = 'Location request timed out. Please try again.';
                    break;
                default:
                    msg = 'Unable to get location. Please try again.';
            }

            showLocationError(msg);

            // Re-enable button so user can try again
            btn.disabled = false;
            btn.innerHTML = '<span class="btn-icon">📍</span> Allow Check & Proceed';
        },
        {
            enableHighAccuracy: false,
            timeout: 15000,
            maximumAge: 0,
        }
    );
}

function showLocationError(msg) {
    const statusBox = document.getElementById('location-status');
    const statusText = document.getElementById('location-status-text');
    statusText.textContent = msg;
    statusBox.classList.remove('hidden');
}


/**
 * Step 2: Render Google reCAPTCHA v2
 */
function renderRecaptcha() {
    if (!recaptchaSiteKey) {
        showError('reCAPTCHA configuration error. Please contact admin.');
        return;
    }

    // If grecaptcha is loaded, render now
    if (typeof grecaptcha !== 'undefined' && grecaptcha.render) {
        doRenderRecaptcha();
    }
    // Otherwise, onRecaptchaLoad will be called by the script tag
}

function onRecaptchaLoad() {
    // Called by the reCAPTCHA script's onload callback
    if (document.getElementById('step-captcha') &&
        !document.getElementById('step-captcha').classList.contains('hidden')) {
        doRenderRecaptcha();
    }
}

function doRenderRecaptcha() {
    if (recaptchaWidgetId !== null) return; // Already rendered

    try {
        recaptchaWidgetId = grecaptcha.render('recaptcha-container', {
            sitekey: recaptchaSiteKey,
            theme: 'dark',
            callback: onRecaptchaSuccess,
            'expired-callback': onRecaptchaExpired,
            'error-callback': onRecaptchaError,
        });
    } catch (e) {
        console.error('reCAPTCHA render error:', e);
    }
}

function onRecaptchaSuccess(token) {
    recaptchaToken = token;
    // Show the verify button
    document.getElementById('btn-verify').classList.remove('hidden');
    // Hide any error
    document.getElementById('captcha-status').classList.add('hidden');
}

function onRecaptchaExpired() {
    recaptchaToken = null;
    document.getElementById('btn-verify').classList.add('hidden');
    showCaptchaStatus('⚠️', 'reCAPTCHA expired. Please solve it again.');
}

function onRecaptchaError() {
    showCaptchaStatus('❌', 'reCAPTCHA error. Please refresh and try again.');
}


/**
 * Step 3: Submit verification to backend
 */
async function submitVerification() {
    if (!recaptchaToken) {
        showCaptchaStatus('⚠️', 'Please complete the reCAPTCHA first.');
        return;
    }

    if (!userLocation) {
        showCaptchaStatus('⚠️', 'Location data missing. Please refresh and try again.');
        return;
    }

    // Show processing
    showStep(stepProcessing);

    try {
        const resp = await fetch(`${API_BASE}/api/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                token: TOKEN,
                recaptcha_token: recaptchaToken,
                location: userLocation,
                user_agent: navigator.userAgent,
                screen_info: `${screen.width}x${screen.height}`,
            }),
        });

        const data = await resp.json();

        if (data.success) {
            showSuccess();
        } else {
            showError(data.error || 'Verification failed. Please try again.');
        }
    } catch (err) {
        showError('Network error. Please check your connection and try again.');
    }
}


// ── Helpers ──

function showStep(stepEl) {
    [stepLocation, stepCaptcha, stepProcessing, stepSuccess, stepError].forEach(el => {
        if (el) el.classList.add('hidden');
    });
    if (stepEl) {
        stepEl.classList.remove('hidden');
        stepEl.classList.add('fade-in');
    }
}

function showSuccess() {
    showStep(stepSuccess);
}

function showError(msg) {
    const errorMsg = document.getElementById('error-message');
    if (errorMsg) errorMsg.textContent = msg;
    showStep(stepError);
}

function showCaptchaStatus(icon, msg) {
    const box = document.getElementById('captcha-status');
    const text = document.getElementById('captcha-status-text');
    box.querySelector('.status-icon').textContent = icon;
    text.textContent = msg;
    box.classList.remove('hidden');
}

// Make onRecaptchaLoad globally accessible
window.onRecaptchaLoad = onRecaptchaLoad;
