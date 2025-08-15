module.exports = {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      keyframes: {
        'typing-wave': {
          '0%, 60%, 100%': { transform: 'translateY(0)' },  
          '30%': { transform: 'translateY(3px)' },
        },
      },
      animation: {
        'typing-wave': 'typing-wave 1.2s ease-in-out infinite',
      },
    },
  },
};








