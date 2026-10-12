// SpartanGO Terms and Conditions (prototype).
// When you change the text in a way users should re-accept, bump TERMS_VERSION here AND in
// backend/app/config.py (TERMS_VERSION). Sign-up sends this version; the backend rejects an old one.
// Have Dr. Nwosu (and NSU, if the app is ever used beyond the capstone) review this text.

export const TERMS_VERSION = '2026-10-12';
export const TERMS_UPDATED = 'October 12, 2026';

export interface TermsSection { title: string; body: string[] }

export const termsIntro =
  'Please read these terms before using SpartanGO. By creating an account, you agree to them. ' +
  'They are written in plain language because this is a student prototype, not a commercial product.';

export const terms: TermsSection[] = [
  {
    title: '1. What SpartanGO is',
    body: [
      'SpartanGO is a prototype app built by Norfolk State University computer science students for their senior capstone (CSC498/CSC499).',
      'It is not an official NSU service. It is not run or endorsed by NSU Transportation or any NSU office unless NSU says so in writing.',
    ],
  },
  {
    title: '2. Who can use it',
    body: [
      'Student accounts require an NSU email address. Driver and administrator accounts are created by the project team for testing.',
      'Keep your password private. You are responsible for activity on your account.',
    ],
  },
  {
    title: '3. The ride pass is not an official ID',
    body: [
      'The QR ride pass is a prototype for testing boarding. It does not replace your NSU student ID. A driver may still ask to see your official ID.',
    ],
  },
  {
    title: '4. Shuttle times are estimates',
    body: [
      'Shuttle locations and arrival times may be delayed, wrong, simulated for testing, or unavailable. Do not rely on SpartanGO when timing really matters.',
      'Official NSU schedules and announcements always take priority over the app.',
    ],
  },
  {
    title: '5. Using the app responsibly',
    body: [
      'Do not submit fake or repeated ride requests.',
      'Do not share, screenshot, or copy your ride pass for someone else to use.',
      'Only authorized drivers may scan passes.',
      "Do not try to access other people's accounts, interfere with the app or its servers, or test its security without the team's written permission.",
      'If you find a bug or security problem, report it to the team instead of using it.',
    ],
  },
  {
    title: '6. Information we collect',
    body: [
      'Account: your name, NSU email, student ID number, and password (stored only in scrambled, hashed form; we cannot read it).',
      'Activity: ride requests (route, pickup and drop-off stops, times) and pass scans (time and shuttle).',
      'Your location: if you allow it, your phone uses your location only to show you on the map. It stays on your device and is not sent to SpartanGO.',
      'Notifications: arrival alerts are optional and can be turned off at any time in your phone settings.',
    ],
  },
  {
    title: '7. How your information is used and kept',
    body: [
      'We use your information only to run the app, test it, and fix problems for the capstone project.',
      'Only the project team and our faculty advisor can access it. We do not sell it or use it for advertising.',
      'We keep it only as long as the project needs it and delete it when the capstone ends, or sooner if you ask.',
    ],
  },
  {
    title: '8. Your account',
    body: [
      'You can ask the team to delete your account and data at any time.',
      'The team may suspend accounts that break these terms.',
    ],
  },
  {
    title: '9. No guarantees',
    body: [
      'SpartanGO is provided as-is for education and testing. It may change, have errors, or stop working at any time, including when the capstone ends.',
    ],
  },
  {
    title: '10. Changes to these terms',
    body: [
      'If these terms change in an important way, the app will show the new version and ask you to accept it.',
    ],
  },
];
