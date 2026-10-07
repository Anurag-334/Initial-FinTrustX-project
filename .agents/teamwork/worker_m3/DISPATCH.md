## 2026-10-05T19:32:54Z
You are Worker M3: Frontend UI Engineer.
Working directory: d:\Projects\Credit-risk-ai\.agents\teamwork\worker_m3
Project Root: d:\Projects\Credit-risk-ai

You MUST read the following files before writing any code:
1. `d:\Projects\Credit-risk-ai\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `d:\Projects\Credit-risk-ai\project.md`
3. `d:\Projects\Credit-risk-ai\GEMINI.md`
4. `d:\Projects\Credit-risk-ai\.agents\teamwork\orchestrator_2\PROJECT.md`
5. `d:\Projects\Credit-risk-ai\.agents\teamwork\explorer_survey_3\report.md`
6. `d:\Projects\Credit-risk-ai\.agents\teamwork\explorer_survey_3\handoff.md`

File Ownership:
You have exclusive write ownership over:
- `frontend/index.html`
- `frontend/js/app.js`
- `frontend/css/style.css` (if styling adjustments needed)
You MUST NOT edit files in `api/` or `scripts/`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. Update `frontend/index.html`:
   - In `<form id="assessment-form">`, at the top of Section A (Personal Information), add an Applicant ID input field:
     ```html
     <div class="form-group">
       <label for="SK_ID_CURR">Applicant ID</label>
       <input type="number" id="SK_ID_CURR" name="SK_ID_CURR" class="form-input" placeholder="e.g. 100002" min="100000">
       <span class="field-hint">Optional: Enter ID to fetch historical bureau & loan records</span>
     </div>
     ```
   - Ensure styling matches existing form controls and theme.
2. Update `frontend/js/app.js`:
   - In `loadPresetProfile(profileKey)`:
     Ensure the preset's `SK_ID_CURR` (`100003` for prime, `100045` for moderate, `100002` for subprime) correctly populates into the `SK_ID_CURR` input field (`form.elements['SK_ID_CURR'].value = val`).
   - In `collectFormData()`:
     Read `const rawId = form.elements['SK_ID_CURR']?.value?.trim()`.
     If `rawId` is not empty and is a valid integer (`!isNaN(parseInt(rawId, 10))`), include `SK_ID_CURR: parseInt(rawId, 10)`.
     If `rawId` is empty or not provided, do NOT fall back to `100001`! Omit `SK_ID_CURR` or set it to `null` so that when a user clears the field, the API receives an ID-less request (verifying backward compatibility).
3. Validate HTML and JS for syntax errors.
4. Write your handoff report to `d:\Projects\Credit-risk-ai\.agents\teamwork\worker_m3\handoff.md`.
When finished, send a brief message with your handoff path.
