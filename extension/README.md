# coolkit Copilot (browser extension)

Like Teal, Huntr and Simplify's extensions, but backed by your own coolkit server.

- **Save job**: reads the job page (JSON-LD `JobPosting` first, then LinkedIn/Naukri/Greenhouse heuristics), logs it to your applications tracker, and shows your ATS match score with matched and missing skills.
- **Autofill**: fills name, contact, links, experience, notice period, salary, visa and EEO fields from your profile. Works with React-based forms (Greenhouse, Lever, Ashby, Workday). Always review the form before you submit.

## Install
1. Start the backend: `./run.sh --back`
2. Open `chrome://extensions`, turn on **Developer mode**, click **Load unpacked**, and select this `extension/` folder.
3. Open the popup and sign in with your coolkit account (the API URL defaults to `http://localhost:8000`).

For a deployed backend, add its origin to `host_permissions` in `manifest.json`.
