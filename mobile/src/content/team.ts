// Edit this file to update the "About the team" screen. Leave `role` empty to hide it.
export interface Member { name: string; role: string }

export const team: Member[] = [
  { name: 'Tijaina Hill', role: '' },
  { name: 'Dennis Jordan', role: '' },
  { name: 'Jaden Lunsford', role: '' },
  { name: "Ty'vaughn Daniels", role: '' },
  { name: 'HerMajesty Williamson', role: '' },
];

export const advisor = 'Dr. Nwosu';
export const course = 'CSC498 / CSC499 Senior Capstone';
export const department = 'Department of Computer Science, Norfolk State University';

// Fill in once the team has a shared inbox. When empty, the app says to contact the team through the advisor.
export const contactEmail = '';

export const mission =
  'SpartanGO helps NSU students see where the shuttle is, know when it will arrive, request a ride, and board quickly. ' +
  'We built it as our senior capstone to make campus transportation more predictable and easier to use.';
