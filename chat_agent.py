import os
import sys
import json
import urllib.request

def chat_with_groq():
    issue_body = os.environ.get("ISSUE_BODY", "")
    issue_title = os.environ.get("ISSUE_TITLE", "")
    api_key = os.environ.get("GROQ_API_KEY", "")

    if not api_key:
        print("Error: GROQ_API_KEY is not set.")
        sys.exit(1)
    
    if "chat" not in issue_title.lower():
        # Only respond if the issue title contains "chat"
        print("This issue is not a chat request. Ignoring.")
        sys.exit(0)

    system_prompt = """
    You are an autonomous AI agent representing Rahul Agarwal on his GitHub profile.
    Your job is to answer questions from visitors who open issues to chat with him.
    Rahul is a Full Stack Developer & AI/ML Specialist. 
    He specializes in Python, React, Llama-3, Computer Vision, and high-fidelity web experiences.
    Keep your responses friendly, slightly futuristic/hacker-themed, and concise. 
    Always sign off your messages as '- Rahul\\'s AI Agent 🤖'.
    """

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": issue_body}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }

    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            bot_reply = result["choices"][0]["message"]["content"]
            
            # Print specifically for the GitHub Action to capture
            # Using a delimiter to safely capture multi-line output
            print("===BOT_REPLY_START===")
            print(bot_reply)
            print("===BOT_REPLY_END===")
            
    except Exception as e:
        print(f"Error communicating with Groq: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    chat_with_groq()
