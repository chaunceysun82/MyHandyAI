# 🛠️ MyHandyAI – Editing Prompts & Running the App
 
This guide explains how to **edit AI prompts** and **run the Grok models for HandyAI  application** using **Streamlit**.

---

## 1. 🧠 Editing Prompts

All prompt files are located in the `/prompts` folder.

Each file (e.g., `summary_prompt.txt`, `qa_prompt.txt`, etc.) contains specific instructions used by the AI.  
You can **edit these files directly—no code changes are required**.

### 📄 Prompt File Descriptions

| File Name          | Purpose |
|--------------------|---------|
| `summary_prompt.txt` | Instructs the AI to generate a descriptive summary of the user’s problem, including their textual input and any uploaded image. |
| `qa_prompt.txt`       | Asks the AI to generate 3–5 clarifying questions to better understand the user’s issue. |
| `auth_prompt.txt`     | Validates whether a user's answer is relevant and correctly responds to a corresponding question. |
| `explain_prompt.txt`  | When the answer doesn’t fit the question, this prompt helps the AI explain what the question is actually asking—in user-friendly language. |
| `steps_prompt.txt`    | Generates a detailed step-by-step repair or solution guide, including safety warnings and potential risks. |
| `tools_prompt.txt`    | Recommends missing tools and materials based on the problem summary and Q&A. |
| `chat_system_prompt.txt` | Provides ongoing context and maintains continuity across the live chat session. |

### 💬 Adding Comments to Prompts

You can add comments for other editors by starting a line with `#`.  
These comments are **ignored by the application and the AI**.

**Example:**
```txt
# This is a comment and will not be sent to the AI.
You are a helpful assistant. Problem: {query}
```

---

## 2. 🚀 Running the Streamlit App

Follow these steps to run MyHandyAI on your local machine:

### a. Install Python

Ensure you have **Python 3.8 or newer** installed.  
Download it from: [https://www.python.org/downloads](https://www.python.org/downloads)

---

### b. Install Required Libraries

Open your terminal (Command Prompt, PowerShell, or Terminal app).

Navigate to the project folder (where `requirements.txt` is located), then run:

```bash
pip install -r requirements.txt
```

This installs Streamlit and all other required dependencies.

---

### c. Start the App

Once dependencies are installed, run:

```bash
streamlit run llmtest.py
```

This will launch the app in your default browser.  
If it doesn’t open automatically, copy the URL displayed in the terminal and paste it into your browser.

---

## 3. 🔄 Editing Prompts While the App is Running (Hot Reload)

You can **edit prompt files inside `/prompts`** even while the app is running.

To see your changes:

- Save the file.
- **Refresh your browser tab** where the app is open.
- The updated prompts will be reloaded automatically.