/**
 * OTP Hub — Verification Flow
 * 
 * Flow:
 * 1. Page loads → shows location step (no backend call needed)
 * 2. User grants location
 * 3. THEN contacts backend to get reCAPTCHA key
 * 4. User solves reCAPTCHA
 * 5. Submits everything to backend
 */

// ── Configuration ──
// Set this to your VPS IP/domain where the bot runs.
const API_BASE = "http://161.118.182.184:8080";

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


// ═══════════════════════════════
// FLOATING PARTICLES
// ═══════════════════════════════

(function initParticles() {
    const canvas = document.getElementById('particles-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let w, h;
    const particles = [];
    const PARTICLE_COUNT = 40;

    function resize() {
        w = canvas.width = window.innerWidth;
        h = canvas.height = window.innerHeight;
    }

    resize();
    window.addEventListener('resize', resize);

    for (let i = 0; i < PARTICLE_COUNT; i++) {
        particles.push({
            x: Math.random() * w,
            y: Math.random() * h,
            vx: (Math.random() - 0.5) * 0.3,
            vy: (Math.random() - 0.5) * 0.3,
            r: Math.random() * 1.5 + 0.5,
            alpha: Math.random() * 0.3 + 0.05,
        });
    }

    function draw() {
        ctx.clearRect(0, 0, w, h);

        for (const p of particles) {
            p.x += p.vx;
            p.y += p.vy;

            if (p.x < 0) p.x = w;
            if (p.x > w) p.x = 0;
            if (p.y < 0) p.y = h;
            if (p.y > h) p.y = 0;

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(99, 102, 241, ${p.alpha})`;
            ctx.fill();
        }

        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 120) {
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.strokeStyle = `rgba(99, 102, 241, ${0.04 * (1 - dist / 120)})`;
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                }
            }
        }

        requestAnimationFrame(draw);
    }

    draw();
})();


// ═══════════════════════════════
// INITIALIZATION
// ═══════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    // Only check if token exists — do NOT call backend yet
    if (!TOKEN) {
        showError('Invalid verification link. Please use the link from the Telegram bot.');
        return;
    }

    // Token exists → show location step (no backend call needed)
    // Backend will be contacted AFTER location is granted
});


// ═══════════════════════════════
// STEP 1: LOCATION
// ═══════════════════════════════

function requestLocation() {
    const btn = document.getElementById('btn-location');
    const statusBox = document.getElementById('location-status');

    btn.disabled = true;
    btn.querySelector('span').textContent = 'Requesting Permission...';

    if (!navigator.geolocation) {
        showLocationError('Your browser does not support location. Please use a modern browser.');
        btn.disabled = false;
        btn.querySelector('span').textContent = 'Allow Check & Proceed';
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (position) => {
            userLocation = {
                lat: position.coords.latitude,
                lng: position.coords.longitude,
                accuracy: position.coords.accuracy,
            };

            statusBox.classList.add('hidden');

            // NOW contact backend to get reCAPTCHA key and validate token
            fetchSessionAndProceed();
        },
        (error) => {
            let msg = '';
            switch (error.code) {
                case error.PERMISSION_DENIED:
                    msg = 'Location permission denied. Tap the button again and select "Allow" to proceed.';
                    break;
                case error.POSITION_UNAVAILABLE:
                    msg = 'Location unavailable. Please enable GPS/location services and try again.';
                    break;
                case error.TIMEOUT:
                    msg = 'Location request timed out. Please try again.';
                    break;
                default:
                    msg = 'Unable to retrieve location. Please try again.';
            }

            showLocationError(msg);
            btn.disabled = false;
            btn.querySelector('span').textContent = 'Allow Check & Proceed';
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


// ═══════════════════════════════
// FETCH SESSION (after location granted)
// ═══════════════════════════════

async function fetchSessionAndProceed() {
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

        // Show reCAPTCHA step
        showStep(stepCaptcha);
        renderRecaptcha();

    } catch (err) {
        showError('Cannot connect to verification server. Please try again later.');
    }
}


// ═══════════════════════════════
// STEP 2: RECAPTCHA
// ═══════════════════════════════

function renderRecaptcha() {
    if (!recaptchaSiteKey) {
        showError('reCAPTCHA configuration error. Contact the admin.');
        return;
    }

    if (typeof grecaptcha !== 'undefined' && grecaptcha.render) {
        doRenderRecaptcha();
    }
    // If grecaptcha not loaded yet, onRecaptchaLoad will handle it
}

function onRecaptchaLoad() {
    // Called by the reCAPTCHA script's onload callback
    if (document.getElementById('step-captcha') &&
        !document.getElementById('step-captcha').classList.contains('hidden')) {
        doRenderRecaptcha();
    }
}

function doRenderRecaptcha() {
    if (recaptchaWidgetId !== null) return;

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
    document.getElementById('btn-verify').classList.remove('hidden');
    document.getElementById('captcha-status').classList.add('hidden');
}

function onRecaptchaExpired() {
    recaptchaToken = null;
    document.getElementById('btn-verify').classList.add('hidden');
    showCaptchaStatus('reCAPTCHA expired. Please solve it again.');
}

function onRecaptchaError() {
    showCaptchaStatus('reCAPTCHA error. Please refresh and try again.');
}


// ═══════════════════════════════
// STEP 3: SUBMIT VERIFICATION
// ═══════════════════════════════

async function submitVerification() {
    if (!recaptchaToken) {
        showCaptchaStatus('Please complete the reCAPTCHA first.');
        return;
    }

    if (!userLocation) {
        showCaptchaStatus('Location data missing. Please refresh and try again.');
        return;
    }

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


// ═══════════════════════════════
// HELPERS
// ═══════════════════════════════

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

function showCaptchaStatus(msg) {
    const box = document.getElementById('captcha-status');
    const text = document.getElementById('captcha-status-text');
    text.textContent = msg;
    box.classList.remove('hidden');
}

window.onRecaptchaLoad = onRecaptchaLoad;
