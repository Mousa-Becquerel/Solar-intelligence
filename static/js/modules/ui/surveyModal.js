/**
 * Survey Modal Management
 * Handles user profiling surveys (Stage 1 and Stage 2)
 */

import { createElement } from '../../utils/dom.js';

// Survey State
let currentSurveyStep = 1;
const totalSurveySteps = 5;

let currentSurveyStage2Step = 1;
const totalSurveyStage2Steps = 5;

// ===========================================
// SUCCESS MODAL
// ===========================================

function showSuccessModal(message, newQueryCount) {
    // Create modal overlay
    const overlay = createElement('div', {
        classes: 'success-modal-overlay'
    });

    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.6);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.2s ease;
    `;

    // Create modal content
    const modal = createElement('div', {
        classes: 'success-modal-content'
    });

    modal.style.cssText = `
        background: white;
        border-radius: 16px;
        padding: 2.5rem;
        max-width: 500px;
        width: 90%;
        text-align: center;
        border: 1px solid rgba(30, 58, 138, 0.1);
        animation: slideUp 0.3s ease;
    `;

    modal.innerHTML = `
        <div style="font-size: 4rem; margin-bottom: 1rem;">🎉</div>
        <h2 style="color: #1e3a8a; margin-bottom: 1rem; font-size: 1.75rem; font-weight: 600;">
            Thank You for Completing the Survey!
        </h2>
        <p style="color: #4b5563; font-size: 1.1rem; margin-bottom: 1.5rem; line-height: 1.6;">
            You've unlocked <strong style="color: #f59e0b;">5 more queries</strong>!<br>
            You now have <strong style="color: #10b981;">${newQueryCount} queries</strong> available.
        </p>
        <div style="background: #fef3c7; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; border-left: 4px solid #f59e0b;">
            <p style="color: #92400e; margin: 0; font-size: 0.95rem;">
                <strong>Reloading to activate your bonus queries...</strong>
            </p>
        </div>
        <button id="success-modal-ok-btn" style="
            background: #FFB74D;
            color: #1e3a8a;
            padding: 0.875rem 2.5rem;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s ease;
            position: relative;
            overflow: hidden;
        ">
            OK
        </button>
    `;

    // Add animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        #success-modal-ok-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0);
            transition: background 0.2s ease;
            pointer-events: none;
        }
        #success-modal-ok-btn:hover::before {
            background: rgba(0, 0, 0, 0.08);
        }
        #success-modal-ok-btn:active::before {
            background: rgba(0, 0, 0, 0.12);
        }
    `;
    document.head.appendChild(style);

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // Handle OK button click
    const okButton = modal.querySelector('#success-modal-ok-btn');
    okButton.addEventListener('click', () => {
        window.location.reload();
    });

    // Auto-reload after 5 seconds if user doesn't click OK
    setTimeout(() => {
        window.location.reload();
    }, 5000);
}

// ===========================================
// STAGE 1 SURVEY FUNCTIONS
// ===========================================

export function showSurveyModal() {
    const modal = document.getElementById('survey-modal');
    if (!modal) {
        console.error('Survey modal not found');
        return;
    }

    modal.style.display = 'flex';

    // Reset form and step
    const form = document.getElementById('user-survey-form');
    if (form) {
        form.reset();
    }

    const roleOther = document.querySelector('input[name="role_other"]');
    if (roleOther) {
        roleOther.style.display = 'none';
    }

    currentSurveyStep = 1;
    showSurveyStep(1);
    updateSurveyProgress();
}

export function closeSurveyModal() {
    const modal = document.getElementById('survey-modal');
    if (modal) {
        modal.style.display = 'none';
    }
    currentSurveyStep = 1;
}

function showSurveyStep(stepNumber) {
    // Hide all steps
    document.querySelectorAll('.survey-step').forEach(step => {
        step.style.display = 'none';
    });

    // Show current step
    const currentStep = document.querySelector(`.survey-step[data-step="${stepNumber}"]`);
    if (currentStep) {
        currentStep.style.display = 'block';
    }

    // Update button visibility
    const prevBtn = document.getElementById('survey-prev-btn');
    const nextBtn = document.getElementById('survey-next-btn');
    const submitBtn = document.getElementById('survey-submit-btn');

    if (prevBtn) prevBtn.style.display = stepNumber === 1 ? 'none' : 'block';
    if (nextBtn) nextBtn.style.display = stepNumber === totalSurveySteps ? 'none' : 'block';
    if (submitBtn) submitBtn.style.display = stepNumber === totalSurveySteps ? 'block' : 'none';
}

function showSurveyError(message, surveyId = 'survey-error') {
    const errorDiv = document.getElementById(surveyId);
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.classList.add('show');

        // Auto-hide after 5 seconds
        setTimeout(() => {
            errorDiv.classList.remove('show');
        }, 5000);

        // Scroll to top of form to show error
        errorDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function validateCurrentStep() {
    if (currentSurveyStep === 1) {
        // Validate role selection
        const role = document.querySelector('select[name="role"]')?.value;
        if (!role) {
            showSurveyError('Please select your role');
            return false;
        }
        if (role === 'other') {
            const roleOther = document.querySelector('input[name="role_other"]')?.value.trim();
            if (!roleOther) {
                showSurveyError('Please specify your role');
                return false;
            }
        }
    } else if (currentSurveyStep === 2) {
        // Validate at least one region
        const regions = document.querySelectorAll('input[name="region"]:checked');
        if (regions.length === 0) {
            showSurveyError('Please select at least one region');
            return false;
        }
    } else if (currentSurveyStep === 3) {
        // Validate familiarity level
        const familiarity = document.querySelector('select[name="familiarity"]')?.value;
        if (!familiarity) {
            showSurveyError('Please select your familiarity level');
            return false;
        }
    } else if (currentSurveyStep === 4) {
        // Validate at least one insight type
        const insights = document.querySelectorAll('input[name="insights"]:checked');
        if (insights.length === 0) {
            showSurveyError('Please select at least one type of insight');
            return false;
        }
    }

    return true;
}

export function nextSurveyStep() {
    if (!validateCurrentStep()) {
        return;
    }

    if (currentSurveyStep < totalSurveySteps) {
        currentSurveyStep++;
        showSurveyStep(currentSurveyStep);
        updateSurveyProgress();
    }
}

export function prevSurveyStep() {
    if (currentSurveyStep > 1) {
        currentSurveyStep--;
        showSurveyStep(currentSurveyStep);
        updateSurveyProgress();
    }
}

function updateSurveyProgress() {
    const progressFill = document.getElementById('survey-progress-fill');
    const currentStepSpan = document.getElementById('survey-current-step');

    if (progressFill) {
        const progressPercent = (currentSurveyStep / totalSurveySteps) * 100;
        progressFill.style.width = `${progressPercent}%`;
    }

    if (currentStepSpan) {
        currentStepSpan.textContent = currentSurveyStep;
    }
}

export async function submitSurvey(event) {
    event.preventDefault();

    const form = document.getElementById('user-survey-form');
    const formData = new FormData(form);

    // Validate at least one region is selected
    const regions = formData.getAll('region');
    if (regions.length === 0) {
        showSurveyError('Please select at least one region of interest');
        return;
    }

    // Validate at least one insight type is selected
    const insights = formData.getAll('insights');
    if (insights.length === 0) {
        showSurveyError('Please select at least one type of insight');
        return;
    }

    // Prepare data
    const surveyData = {
        role: formData.get('role'),
        role_other: formData.get('role') === 'other' ? formData.get('role_other') : null,
        regions: regions,
        familiarity: formData.get('familiarity'),
        insights: insights,
        tailored: formData.get('tailored')
    };

    try {
        // Get CSRF token
        const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';

        const response = await fetch('/submit-user-survey', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(surveyData)
        });

        const data = await response.json();

        if (response.ok && data.success) {
            closeSurveyModal();

            // Show success modal
            showSuccessModal('Thank you for completing the survey!', data.new_query_count);
        } else {
            showSurveyError(data.message || 'Failed to submit survey. Please try again.');
        }
    } catch (error) {
        console.error('Error submitting survey:', error);
        showSurveyError('Failed to submit survey. Please try again.');
    }
}

// ===========================================
// STAGE 2 SURVEY FUNCTIONS
// ===========================================

export function showSurveyStage2Modal() {
    const modal = document.getElementById('survey-stage2-modal');
    if (!modal) {
        console.error('Survey Stage 2 modal not found');
        return;
    }

    modal.style.display = 'flex';

    // Reset form and step
    const form = document.getElementById('user-survey-stage2-form');
    if (form) {
        form.reset();
    }

    const workFocusOther = document.querySelector('input[name="work_focus_other"]');
    if (workFocusOther) {
        workFocusOther.style.display = 'none';
    }

    const technologiesOther = document.querySelector('input[name="technologies_other"]');
    if (technologiesOther) {
        technologiesOther.style.display = 'none';
    }

    // Reset challenge counter
    const challengeCounter = document.getElementById('challenge-counter');
    if (challengeCounter) {
        challengeCounter.textContent = 'Select up to 3 challenges (0 selected)';
    }

    // Re-enable all challenge checkboxes
    document.querySelectorAll('input[name="challenge"]').forEach(cb => {
        cb.disabled = false;
        cb.parentElement.style.opacity = '1';
    });

    currentSurveyStage2Step = 1;
    showSurveyStage2Step(1);
    updateSurveyStage2Progress();
}

export function closeSurveyStage2Modal() {
    const modal = document.getElementById('survey-stage2-modal');
    if (modal) {
        modal.style.display = 'none';
    }
    currentSurveyStage2Step = 1;
}

function showSurveyStage2Step(stepNumber) {
    // Hide all steps
    document.querySelectorAll('#user-survey-stage2-form .survey-step').forEach(step => {
        step.style.display = 'none';
    });

    // Show current step
    const currentStep = document.querySelector(`#user-survey-stage2-form .survey-step[data-step="${stepNumber}"]`);
    if (currentStep) {
        currentStep.style.display = 'block';
    }

    // Update button visibility
    const prevBtn = document.getElementById('survey-stage2-prev-btn');
    const nextBtn = document.getElementById('survey-stage2-next-btn');
    const submitBtn = document.getElementById('survey-stage2-submit-btn');

    if (prevBtn) prevBtn.style.display = stepNumber === 1 ? 'none' : 'block';
    if (nextBtn) nextBtn.style.display = stepNumber === totalSurveyStage2Steps ? 'none' : 'block';
    if (submitBtn) submitBtn.style.display = stepNumber === totalSurveyStage2Steps ? 'block' : 'none';
}

function validateCurrentStage2Step() {
    if (currentSurveyStage2Step === 1) {
        const workFocus = document.querySelector('select[name="work_focus"]')?.value;
        if (!workFocus) {
            showSurveyError('Please select your work focus', 'survey-stage2-error');
            return false;
        }
        if (workFocus === 'other') {
            const workFocusOther = document.querySelector('input[name="work_focus_other"]')?.value.trim();
            if (!workFocusOther) {
                showSurveyError('Please specify your work focus', 'survey-stage2-error');
                return false;
            }
        }
    } else if (currentSurveyStage2Step === 2) {
        const segments = document.querySelectorAll('input[name="pv_segment"]:checked');
        if (segments.length === 0) {
            showSurveyError('Please select at least one PV segment', 'survey-stage2-error');
            return false;
        }
    } else if (currentSurveyStage2Step === 3) {
        const technologies = document.querySelectorAll('input[name="technology"]:checked');
        if (technologies.length === 0) {
            showSurveyError('Please select at least one technology', 'survey-stage2-error');
            return false;
        }
    } else if (currentSurveyStage2Step === 4) {
        const challenges = document.querySelectorAll('input[name="challenge"]:checked');
        if (challenges.length === 0) {
            showSurveyError('Please select at least one challenge', 'survey-stage2-error');
            return false;
        }
    }

    return true;
}

export function nextSurveyStage2Step() {
    if (!validateCurrentStage2Step()) {
        return;
    }

    if (currentSurveyStage2Step < totalSurveyStage2Steps) {
        currentSurveyStage2Step++;
        showSurveyStage2Step(currentSurveyStage2Step);
        updateSurveyStage2Progress();
    }
}

export function prevSurveyStage2Step() {
    if (currentSurveyStage2Step > 1) {
        currentSurveyStage2Step--;
        showSurveyStage2Step(currentSurveyStage2Step);
        updateSurveyStage2Progress();
    }
}

function updateSurveyStage2Progress() {
    const progressFill = document.getElementById('survey-stage2-progress-fill');
    const currentStepSpan = document.getElementById('survey-stage2-current-step');

    if (progressFill) {
        const progressPercent = (currentSurveyStage2Step / totalSurveyStage2Steps) * 100;
        progressFill.style.width = `${progressPercent}%`;
    }

    if (currentStepSpan) {
        currentStepSpan.textContent = currentSurveyStage2Step;
    }
}

export async function submitSurveyStage2(event) {
    event.preventDefault();

    const form = document.getElementById('user-survey-stage2-form');
    const formData = new FormData(form);

    // Validate selections
    const pvSegments = formData.getAll('pv_segment');
    if (pvSegments.length === 0) {
        showSurveyError('Please select at least one PV segment', 'survey-stage2-error');
        return;
    }

    const technologies = formData.getAll('technology');
    if (technologies.length === 0) {
        showSurveyError('Please select at least one technology', 'survey-stage2-error');
        return;
    }

    const challenges = formData.getAll('challenge');
    if (challenges.length === 0 || challenges.length > 3) {
        showSurveyError('Please select 1-3 challenges', 'survey-stage2-error');
        return;
    }

    // Prepare data
    const surveyData = {
        work_focus: formData.get('work_focus'),
        work_focus_other: formData.get('work_focus') === 'other' ? formData.get('work_focus_other') : null,
        pv_segments: pvSegments,
        technologies: technologies,
        technologies_other: technologies.includes('other') ? formData.get('technologies_other') : null,
        challenges: challenges,
        weekly_insight: formData.get('weekly_insight') || null
    };

    try {
        const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';

        const response = await fetch('/submit-user-survey-stage2', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(surveyData)
        });

        const data = await response.json();

        if (response.ok && data.success) {
            closeSurveyStage2Modal();

            // Show success modal
            showSuccessModal('Thank you for completing the survey!', data.new_query_count);
        } else {
            showSurveyError(data.message || 'Failed to submit survey. Please try again.', 'survey-stage2-error');
        }
    } catch (error) {
        console.error('Error submitting Stage 2 survey:', error);
        showSurveyError('Failed to submit survey. Please try again.', 'survey-stage2-error');
    }
}

// ===========================================
// INITIALIZATION
// ===========================================

export function initializeSurveyModal() {
    // Handle role "Other" selection
    const roleSelect = document.querySelector('select[name="role"]');
    const roleOtherInput = document.querySelector('input[name="role_other"]');

    roleSelect?.addEventListener('change', function() {
        if (this.value === 'other') {
            roleOtherInput.style.display = 'block';
            roleOtherInput.required = true;
        } else {
            roleOtherInput.style.display = 'none';
            roleOtherInput.required = false;
        }
    });

    // Form submission
    document.getElementById('user-survey-form')?.addEventListener('submit', submitSurvey);

    // Close on outside click
    document.getElementById('survey-modal')?.addEventListener('click', function(e) {
        if (e.target === this) {
            closeSurveyModal();
        }
    });

    // Stage 2 - Handle work_focus "Other" selection
    const workFocusSelect = document.querySelector('select[name="work_focus"]');
    const workFocusOtherInput = document.querySelector('input[name="work_focus_other"]');

    workFocusSelect?.addEventListener('change', function() {
        if (this.value === 'other') {
            workFocusOtherInput.style.display = 'block';
            workFocusOtherInput.required = true;
        } else {
            workFocusOtherInput.style.display = 'none';
            workFocusOtherInput.required = false;
        }
    });

    // Stage 2 - Handle technologies "Other" selection
    const techOtherCheckbox = document.querySelector('input[name="technology"][value="other"]');
    const techOtherInput = document.querySelector('input[name="technologies_other"]');

    techOtherCheckbox?.addEventListener('change', function() {
        if (this.checked) {
            techOtherInput.style.display = 'block';
        } else {
            techOtherInput.style.display = 'none';
            techOtherInput.value = '';
        }
    });

    // Stage 2 - Challenge counter for max 3 selection
    const challengeCheckboxes = document.querySelectorAll('input[name="challenge"]');
    const challengeCounter = document.getElementById('challenge-counter');

    challengeCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const checkedCount = document.querySelectorAll('input[name="challenge"]:checked').length;

            if (challengeCounter) {
                challengeCounter.textContent = `Select up to 3 challenges (${checkedCount} selected)`;
            }

            if (checkedCount >= 3) {
                challengeCheckboxes.forEach(cb => {
                    if (!cb.checked) {
                        cb.disabled = true;
                        cb.parentElement.style.opacity = '0.5';
                    }
                });
            } else {
                challengeCheckboxes.forEach(cb => {
                    cb.disabled = false;
                    cb.parentElement.style.opacity = '1';
                });
            }
        });
    });

    // Stage 2 form submission
    document.getElementById('user-survey-stage2-form')?.addEventListener('submit', submitSurveyStage2);

    // Stage 2 - Close on outside click
    document.getElementById('survey-stage2-modal')?.addEventListener('click', function(e) {
        if (e.target === this) {
            closeSurveyStage2Modal();
        }
    });

    // Expose functions to window for inline onclick handlers
    window.showSurveyModal = showSurveyModal;
    window.closeSurveyModal = closeSurveyModal;
    window.nextSurveyStep = nextSurveyStep;
    window.prevSurveyStep = prevSurveyStep;

    window.showSurveyStage2Modal = showSurveyStage2Modal;
    window.closeSurveyStage2Modal = closeSurveyStage2Modal;
    window.nextSurveyStage2Step = nextSurveyStage2Step;
    window.prevSurveyStage2Step = prevSurveyStage2Step;
}
