import streamlit as st
import requests
import json
import time

st.set_page_config(
    page_title="TherAIpy",
    page_icon="🧠",
    layout="centered"
)

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Hi there. I'm here to listen. What would you like to talk about today?"
    }]

API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "anthropic/claude-3-haiku"

def count_tokens(messages):
    return len(json.dumps(messages)) // 4

def get_max_response_tokens():
    input_tokens = count_tokens(st.session_state.messages)
    return max(300, 2500 - input_tokens - 100) 

st.title("🧠 TherAIpy")
st.caption("A confidential space to share your thoughts")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def query_openrouter():
    headers = {
        "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
        "Content-Type": "application/json",
        "HTTP-Referer": st.secrets.get("APP_URL", "https://your-app-name.streamlit.app"),
        "X-Title": st.secrets.get("APP_NAME", "AI Therapist")
    }
    
    payload = {
        "model": MODEL,
        "messages": st.session_state.messages,
        "temperature": 0.7,
        "max_tokens": get_max_response_tokens()
    }
    
    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            timeout=20
        )
        
        st.toast(f"API Status: {response.status_code}", icon="🔍")
        
        if response.status_code == 400:
            error_msg = response.json().get("error", {}).get("message", "Bad Request")
            raise ValueError(f"API Validation Error: {error_msg}")
        
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
        
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None

if prompt := st.chat_input("How are you feeling today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        try:
            if count_tokens(st.session_state.messages) > 2400:
                raise ValueError("Conversation too long. Please start a new chat.")
            
            message_placeholder = st.empty()
            message_placeholder.markdown("Thinking...")
            
            start_time = time.time()
            ai_response = query_openrouter()
            
            if not ai_response:
                raise ConnectionError("Failed to get valid API response")
            
            full_response = ""
            for chunk in ai_response.split():
                full_response += chunk + " "
                message_placeholder.markdown(full_response + "▌")
                time.sleep(0.03)
            message_placeholder.markdown(full_response)
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response
            })
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": "I encountered an issue. Please try a shorter message or new chat."
            })

if st.button("Clear Chat"):
    st.session_state.messages = [{
        "role": "assistant",
        "content": "I've cleared our chat history. What would you like to talk about?"
    }]
    st.rerun()
