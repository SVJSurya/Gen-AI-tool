import React, { useState } from 'react';
import axios from 'axios';
import './App.css'; // Import the updated CSS for styling

function App() {
  const [code, setCode] = useState('');  // State to store the user's code input
  const [messages, setMessages] = useState([]); // State to store chat messages

  const handleCodeChange = (e) => {
    setCode(e.target.value);  // Update the code state when the user types
  };

  const handleRunTest = async () => {
    if (!code.trim()) return; // Prevent empty submissions

    // Add the user's code to the chat
    setMessages((prevMessages) => [
      ...prevMessages,
      { sender: 'user', text: code }
    ]);

    try {
      // Send the entered code to the backend for processing
      const response = await axios.post('http://localhost:5000/submit-code', { code });
      
      // Add the response from the backend to the chat
      setMessages((prevMessages) => [
        ...prevMessages,
        { sender: 'bot', text: response.data.message }
      ]);
    } catch (error) {
      console.error("Error running code:", error);
      setMessages((prevMessages) => [
        ...prevMessages,
        { sender: 'bot', text: "An error occurred while processing your code." }
      ]);
    }

    // Clear the input after sending the message
    setCode('');
  };

  return (
    <div className="App">
      <h1>Socratic Teaching Assistant</h1>
      
      <div className="chat-container">
        <div className="chat-box">
          {messages.map((msg, index) => (
            <div key={index} className={`chat-message ${msg.sender}`}>
              <p>{msg.text}</p>
            </div>
          ))}
        </div>
        
        <div className="input-container">
          <textarea
            value={code}
            onChange={handleCodeChange}
            placeholder="Enter your code or question here..."
            rows={3}
          />
          <button onClick={handleRunTest}>Send</button>
        </div>
      </div>
    </div>
  );
}

export default App;
