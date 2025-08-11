// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";

const firebaseConfig = {
  apiKey: process.env.GOOGLE_API_KEY,
  authDomain: "myhandyai-861ac.firebaseapp.com",
  projectId: "myhandyai-861ac",
  storageBucket: "myhandyai-861ac.firebasestorage.app",
  messagingSenderId: "845164324526",
  appId: "1:845164324526:web:c61a60f87fe2ca1052ef3f",
  measurementId: "G-EL43Z3T51F"
};


export const app = initializeApp(firebaseConfig);
