const express = require('express');
const cors = require('cors');
const { google } = require('googleapis'); // Import Google API client

const app = express();
const port = 5000;

app.use(cors());
app.use(express.json());

// Replace with your actual API key
const apiKey = 'AIzaSyBfXLcnxVUeC0htGxwex61x6E-oWBfIIvE';

// POST endpoint to handle the submitted code and call the Google Gen AI API
app.post('/submit-code', async (req, res) => {
    const { code } = req.body;

    try {
        console.log('Received code:', code);

        // Create a client instance of the Gen AI API
        const genai = google.genai({
            version: 'v1',
            auth: apiKey
        });

        // Example usage of Google Gen AI API
        const projectId = 'your-project-id';
        const location = 'your-location';
        const modelName = 'your-model-name';

        const requestBody = {
            // Pass the necessary request body parameters
            // For example:
            'input': {
                'prompt': code
            }
        };

        const response = await genai.projects.locations.models.predict({
            'name': `projects/${projectId}/locations/${location}/models/${modelName}`,
            'requestBody': requestBody
        });

        res.json({ message: 'Code processed by Google Gen AI', data: response.data });
    } catch (error) {
        console.error('Error processing code:', error);
        res.status(500).json({ error: 'Failed to process code using Google Gen AI API' });
    }
});

// Basic infinite loop detector for demonstration purposes
function detectInfiniteLoop(code) {
    // Improve this function to handle more complex scenarios
    return code.includes("while") && !code.includes("i++");
}

app.listen(port, () => {
    console.log(`Backend running on port ${port}`);
});