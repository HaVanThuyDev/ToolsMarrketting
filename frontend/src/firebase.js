/**
 * Firebase Configuration
 * 
 * Firebase Web SDK config for authentication.
 * These keys are public (client-side) — security is handled by Firebase Security Rules.
 */

import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

const firebaseConfig = {
  apiKey: "AIzaSyAkWRF2z4qR7Y3vD7ywOUH5kSoil-gHK0U",
  authDomain: "tools-3eab4.firebaseapp.com",
  projectId: "tools-3eab4",
  storageBucket: "tools-3eab4.firebasestorage.app",
  messagingSenderId: "994338001112",
  appId: "1:994338001112:web:1323cc9f24822f09e947ad",
  measurementId: "G-YGLXKXFD3X"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export default app;
