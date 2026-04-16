// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyDf3J0sIAAks0B9W5i5mOIDBWDM4andWT4",
  authDomain: "opsis-editor.firebaseapp.com",
  projectId: "opsis-editor",
  storageBucket: "opsis-editor.firebasestorage.app",
  messagingSenderId: "772455423288",
  appId: "1:772455423288:web:80643c650300ed4a36b5cd",
  measurementId: "G-FFQ39TN6MQ"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase Authentication and get a reference to the service
export const auth = getAuth(app);
// Initialize Cloud Firestore and get a reference to the service
export const db = getFirestore(app);
export default app;
