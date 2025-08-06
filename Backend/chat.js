const express = require('express');
const cors = require('cors');
const { StreamChat } = require('stream-chat');

const app = express();
app.use(cors()); // Only enable CORS for allowed frontend domains in production

const API_KEY = process.env.API_KEY;
const API_SECRET = process.env.API_SECRET;


const serverClient = StreamChat.getInstance(API_KEY, API_SECRET);

(async () => {
  try {
    await serverClient.upsertUser({
      id: 'bot',
      name: 'bot',
    });
    
  } catch (err) {
    console.error('Error upserting bot user:', err);
  }
})();


app.get('/get-bot-token', (req, res) => {
  const botId = req.query.bot_id; // For example: /get-user-token?user_id=user123

  if (!botId) {
    return res.status(400).json({ error: 'Missing user_id' });
  }

  const token = serverClient.createToken(botId);
  res.json({ token });
});


app.get('/get-user-token', (req, res) => {
  const userId = req.query.user_id; // For example: /get-user-token?user_id=user123

  if (!userId) {
    return res.status(400).json({ error: 'Missing user_id' });
  }

  const token = serverClient.createToken(userId);
  res.json({ token });
});

const PORT = 3001;
app.listen(PORT, () => {
  console.log(`Token server running on http://localhost:${PORT}`);
});
