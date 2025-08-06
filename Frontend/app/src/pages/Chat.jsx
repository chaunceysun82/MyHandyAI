import { StreamChat} from 'stream-chat';
import {Chat as StreamChatProvider, Channel, Window, MessageList, MessageInput} from 'stream-chat-react';
import { useEffect, useState } from 'react';
import 'stream-chat-react/dist/css/v2/index.css';
import {MoonIcon, SunIcon} from '@heroicons/react/24/solid';


const apiKey = 'prwq8q9bm34f';
const chatClient = StreamChat.getInstance(apiKey);

const Chat = () => {
  
  const [channel, setChannel] = useState(null);
  const [theme, setTheme] = useState('str-chat__theme-light');

  const toggleButton = () => {
    setTheme(prev => prev === 'str-chat__theme-light' ? 'str-chat__theme-dark' : 'str-chat__theme-light');
  };

  useEffect(() => {
    const init = async () => {
      try {
        const user = 'userId';
        const bot = 'bot';

        const res = await fetch(`http://localhost:3001/get-user-token?user_id=${user}`);
        const dat = await res.json();

        const res2 = await fetch(`http://localhost:3001/get-bot-token?bot_id=${bot}`);
        const dat2 = await res2.json();

        await chatClient.connectUser(
          {
            id: user,
            name: 'Ekansh',
            // Add avatar if you want
            image: `https://ui-avatars.com/api/?name=Ekansh&background=667eea&color=fff&size=128`
          },
          dat.token
        );

        // Create or get channel
        const channel = chatClient.channel('messaging', `general-${Date.now()}`, {
          name: 'ChatGPT Assistant',
          members: [user, bot],
        });

        

        await channel.watch();
        setChannel(channel);


        const messages = await channel.query({ messages: { limit: 1 } });

        if (messages.messages.length === 0) 
        {
          // Create a temporary bot client to send the intro message
          const botClient = StreamChat.getInstance(apiKey);

          await botClient.connectUser(
            {
              id: bot,
              name: 'bot',
              image: 'https://ui-avatars.com/api/?name=AI+Bot&background=f39c12&color=fff'
            },
            dat2.token
          );

          const botChannel = botClient.channel(channel.type, channel.id);
          
          await botChannel.watch();
          await botChannel.sendMessage({
            text: 'Hi! How can I help you today?',
          });

          // await botClient.disconnectUser(); // Optional cleanup
        }


      } catch (error) 
      {
        console.error('Error initializing chat:', error);
      }
    };

    init();

    // Cleanup on unmount
    return () => {
      if (chatClient) {
        chatClient.disconnectUser();
      }
    };
  }, []);


  return (
    <div style={{ height: '100vh', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      

      <StreamChatProvider client={chatClient} theme={theme}>
        <Channel channel={channel}>
          <Window>
            <div className="absolute top-2 right-4 z-10">
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  onChange={toggleButton}
                  checked={theme === 'str-chat__theme-dark'}
                  className="sr-only"
                />
                <div className={`w-12 h-6 rounded-full p-1 flex items-center transition-all duration-300 relative ${
                  theme === 'str-chat__theme-dark' ? 'bg-[#353437]' : 'bg-[#FAF9F6]'
                }`}
                >
                  <div
                    className={`w-4 h-4 rounded-full flex items-center justify-center shadow-md transform transition-transform duration-300 ${
                      theme === 'str-chat__theme-dark' ? 'translate-x-6 bg-[#4F4E52]' : 'translate-x-0 bg-white'
                    }`}
                  >
                    {theme === 'str-chat__theme-light' ? (
                      <SunIcon className='w-3 h-3  text-yellow-400'/>
                    ) : (
                      <MoonIcon className='w-3 h-3 text-white'/>
                    )}
                  </div>
                </div>
              </label>
            </div>

            <MessageList/>
            <MessageInput 
              focus 
              placeholder="Type your message..."
              audioRecordingEnabled={true}
            />
          </Window>
        </Channel>
      </StreamChatProvider>
      
    </div>
  );
};

export default Chat;
