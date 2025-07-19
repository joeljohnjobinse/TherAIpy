# ======================
# THERAIPY APP WITH WORKING AUTHENTICATION
# ======================

import streamlit as st
import requests
import re
import json
import os
import yaml
import matplotlib.pyplot as plt
from datetime import datetime
from yaml.loader import SafeLoader
from passlib.hash import pbkdf2_sha256
import hmac
import hashlib
import base64
import secrets

# ======================
# PATH SETUP
# ======================
CONFIG_DIR = "config"
USERDATA_DIR = "userdata"
CONFIG_PATH = os.path.join(CONFIG_DIR, "users.yaml")

# Create directories if they don't exist
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(USERDATA_DIR, exist_ok=True)

# ======================
# PAGE CONFIGURATION
# ======================
st.set_page_config(page_title="TherAIpy", layout="wide")

# ======================
# INITIAL STATE SETUP
# ======================
if "user" not in st.session_state:
    st.session_state.user = None
if "auth_status" not in st.session_state:
    st.session_state.auth_status = None
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello, I'm here to listen. What would you like to share today?"}]
if "traits" not in st.session_state:
    st.session_state.traits = {
        "Empathy": 0,
        "Self-Awareness": 0,
        "Anxiety": 0,
        "Optimism": 0,
        "Mood Swings": 0,
        "Confidence": 0
    }
if "page" not in st.session_state:
    st.session_state.page = "Chat"

# ======================
# SECURITY FUNCTIONS
# ======================
def generate_salt():
    """Generate a random salt for password hashing in bytes format"""
    return secrets.token_bytes(16)  # Changed to token_bytes instead of token_hex

def hash_password(password):
    """Hash password with automatically generated salt using PBKDF2-HMAC-SHA256"""
    # Let passlib handle the salt generation and formatting
    return pbkdf2_sha256.hash(password)

def verify_password(password, hashed_password):
    """Verify password against stored hash"""
    return pbkdf2_sha256.verify(password, hashed_password)

# ======================
# AUTHENTICATION SETUP
# ======================
# Initialize config file with proper structure
if not os.path.exists(CONFIG_PATH):
    default_config = {
        "credentials": {  # Changed from "users" to "credentials"
            "usernames": {}  # Added "usernames" level
        },
        "cookie": {
            "expiry_days": 30,
            "key": "some_random_key_here",
            "name": "theraipy_cookie"
        },
        "preauthorized": {
            "emails": []
        }
    }
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(default_config, f)

# Load config safely
try:
    with open(CONFIG_PATH, "r") as file:
        config = yaml.load(file, Loader=SafeLoader)
    if config is None:
        raise Exception("Config file is empty")
except Exception as e:
    st.error(f"Error loading config: {e}")
    st.stop()

# ======================
# LOGIN / REGISTER PAGE
# ======================
if not st.session_state.user:
    st.title("🌿 Welcome to TherAIpy")
    
    auth_tab = st.radio("Choose an option:", ["Login", "Register"], horizontal=True)

    if auth_tab == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
    
        if st.button("Login"):
            if not username or not password:
                st.error("Please enter both username and password")
            elif username in config['credentials']['usernames']:  # Fixed path
                stored_hash = config['credentials']['usernames'][username]['password']
                if verify_password(password, stored_hash):
                    st.session_state.user = username
                    st.session_state.auth_status = True
                    st.success(f"Welcome back, {username}!")
                    st.rerun()
                else:
                    st.error("Incorrect password")
            else:
                st.error("Username not found")

    elif auth_tab == "Register":
        new_user = st.text_input("New Username")
        email = st.text_input("Email (optional)")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
    
        if st.button("Register"):
            if not new_user:
                st.error("Please enter a username")
            elif new_user in config['credentials']['usernames']:
                st.error("Username already exists")
            elif password != confirm:
                st.error("Passwords do not match")
            elif len(password) < 8:
                st.error("Password must be at least 8 characters")
            else:
                try:
                    # Let passlib handle the salt generation and hashing
                    hashed_pw = hash_password(password)
                
                    config['credentials']['usernames'][new_user] = {
                        'email': email,
                        'password': hashed_pw,  # Store the complete hashed password string
                        'name': new_user,
                        'created_at': datetime.now().isoformat()
                    }
                
                    with open(CONFIG_PATH, 'w') as f:
                        yaml.dump(config, f)
                
                    st.success("Registration successful! Please login.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Registration failed: {str(e)}")

    st.stop()

# ======================
# SIDEBAR NAVIGATION
# ======================
with st.sidebar:
    st.title("🌿 TherAIpy")
    st.markdown(f"Welcome, **{st.session_state.user}**")
    
    if st.button("Logout"):
        st.session_state.user = None
        st.session_state.auth_status = None
        st.rerun()
    
    st.divider()
    
    if st.button("💬 Chat", use_container_width=True):
        st.session_state.page = "Chat"
    if st.button("📊 Your Profile", use_container_width=True):
        st.session_state.page = "Profile"
    if st.button("📂 Saved Chats", use_container_width=True):
        st.session_state.page = "Saved"
    st.divider()

    if st.session_state.page == "Chat":
        if st.button("💾 Save Current Chat", use_container_width=True):
            timestamp = datetime.now().isoformat()
            path = os.path.join(USERDATA_DIR, f"{st.session_state.user}_chats.json")
            data = {
                "timestamp": timestamp,
                "messages": st.session_state.messages,
                "traits": st.session_state.traits
            }
            all_data = []
            if os.path.exists(path):
                with open(path) as f:
                    all_data = json.load(f)
            all_data.append(data)
            with open(path, 'w') as f:
                json.dump(all_data, f)
            st.success("Chat saved!")

        if st.button("🧹 Clear Chat", use_container_width=True):
            st.session_state.messages = [{"role": "assistant", "content": "Hello, I'm here to listen. What would you like to share today?"}]
            st.session_state.traits = {k: 0 for k in st.session_state.traits}
            st.rerun()

# ======================
# TRAIT EXTRACTION
# ======================
def update_traits(text):
    patterns = {
        "Empathy": ["understand", "empathize", "feel for", "that sounds hard"],
        "Self-Awareness": ["aware", "reflect", "realize"],
        "Anxiety": ["anxious", "worried", "nervous"],
        "Optimism": ["hope", "bright side", "improve"],
        "Mood Swings": ["mixed feelings", "change a lot"],
        "Confidence": ["you can", "strong", "believe in yourself"]
    }
    for trait, keywords in patterns.items():
        for kw in keywords:
            if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
                st.session_state.traits[trait] += 1

# ======================
# OPENROUTER RESPONSE
# ======================
def get_response(convo):
    prompt = """As an empathetic therapist, craft a response that:
    - Validates the person's feelings naturally
    - Asks thoughtful open-ended questions
    - Helps explore thoughts without being directive
    - Sounds completely natural without instructions
    - Don't describe your tone
    - Don't make any visual gestures, just offer a lending ear and advice if necessary
    
    Current conversation:
    {convo}
    
    Respond in 2-3 sentences:""".format(convo=convo)
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
                "Content-Type": "application/json"
            },
            json={
                "model": "anthropic/claude-3-haiku",
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=20
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        st.error(f"Error getting AI response: {e}")
        return "I'm here for you—can you share a bit more?"
    
# ======================
# DYNAMIC PROFILE SUMMARY
# ======================
def generate_profile_summary(total_traits):
    """Generate a unique, natural-sounding summary using AI"""
    dominant_traits = sorted(total_traits.items(), key=lambda x: x[1], reverse=True)
    traits_text = ", ".join([f"{trait.lower()} ({score})" for trait, score in dominant_traits if score > 0])
    
    prompt = f"""Create a 2-3 sentence personalized summary of someone's emotional patterns based on these trait scores:
    {traits_text}
    
    Guidelines:
    - Sound warm and human, like a therapist would
    - Mention specific patterns but don't list numbers
    - Note both strengths and growth areas
    - Keep it concise and insightful
    - Never use phrases like "based on your data"
    - Write in second person ("You tend to...")
    
    Example good output:
    "You have a thoughtful way of reflecting on your experiences, though sometimes anxious thoughts come through. I notice you often find hopeful perspectives too."
    """
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
                "Content-Type": "application/json"
            },
            json={
                "model": "anthropic/claude-3-haiku",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.8  # More creative variation
            },
            timeout=10
        )
        return response.json()['choices'][0]['message']['content'].strip()
    except:
        # Fallback if API fails
        return "Your emotional patterns show interesting depth across our conversations."

def calculate_total_traits():
    """Calculate cumulative traits from all saved chats"""
    user_chat_file = os.path.join(USERDATA_DIR, f"{st.session_state.user}_chats.json")
    total_traits = {trait: 0 for trait in st.session_state.traits}
    
    if os.path.exists(user_chat_file):
        with open(user_chat_file, 'r') as f:
            all_chats = json.load(f)
        for chat in all_chats:
            for trait, value in chat['traits'].items():
                total_traits[trait] += value
    
    # Add current unsaved chat traits
    for trait, value in st.session_state.traits.items():
        total_traits[trait] += value
        
    return total_traits

# ======================
# MAIN PAGES
# ======================
if st.session_state.page == "Chat":
    st.title("💬 Your Therapy Chat")
    
    # Display chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if user_input := st.chat_input("💭 How are you feeling today?"):
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Get conversation context
        convo = "\n".join(
            f"{m['role']}: {m['content']}" 
            for m in st.session_state.messages[-4:]
        )
        
        # Get and display AI response
        reply = get_response(convo)
        update_traits(reply)
        
        st.session_state.messages.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)

elif st.session_state.page == "Profile":
    st.title("📊 Your Emotional Profile")
    
    total_traits = calculate_total_traits()
    
    st.subheader("About You")
    with st.spinner("Generating insights..."):
        profile_summary = generate_profile_summary(total_traits)
        st.write(profile_summary)

    st.subheader("✨ Summary")
    if sum(total_traits.values()) == 0:
        st.info("No traits detected yet. Let's keep chatting.")
    else:
        good = ["Empathy", "Optimism", "Confidence", "Self-Awareness"]
        bad = ["Anxiety", "Mood Swings"]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**✅ Strengths**")
            for trait in good:
                if total_traits[trait] > 0:
                    st.markdown(f"- {trait}: {total_traits[trait]}")
        with col2:
            st.markdown("**⚠️ Growth Areas**")
            for trait in bad:
                if total_traits[trait] > 0:
                    st.markdown(f"- {trait}: {total_traits[trait]}")

        st.subheader("📈 Trait Trends")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(
            [t for t in total_traits if total_traits[t] > 0],  # Only show traits with scores
            [total_traits[t] for t in total_traits if total_traits[t] > 0],
            color="#6eb5ff"
        )
        ax.set_xlabel("Cumulative Score")
        ax.set_title("Your Emotional Traits Across All Chats")
        ax.invert_yaxis()
        st.pyplot(fig)

elif st.session_state.page == "Saved":
    st.title("📂 Saved Chats")
    user_chat_file = os.path.join(USERDATA_DIR, f"{st.session_state.user}_chats.json")
    
    if os.path.exists(user_chat_file):
        try:
            with open(user_chat_file, 'r') as f:
                all_chats = json.load(f)
            
            if not all_chats:
                st.info("No chats saved yet.")
            else:
                # Create a mapping of display names to chat indices
                chat_names = [f"Chat {i+1}" for i in range(len(all_chats))]
                
                # Check if we have saved names in the chat data
                for i, chat in enumerate(all_chats):
                    if 'display_name' in chat:
                        chat_names[i] = chat['display_name']
                
                # Select a chat to view/edit
                selected_chat_name = st.selectbox(
                    "Select a chat to view:",
                    chat_names,
                    index=len(chat_names)-1  # Default to most recent
                )
                selected_index = chat_names.index(selected_chat_name)
                chat = all_chats[selected_index]
                
                # Rename functionality
                with st.expander("✏️ Rename this chat"):
                    new_name = st.text_input(
                        "New name for this chat:",
                        value=chat.get('display_name', f"Chat {selected_index+1}"),
                        key=f"rename_{selected_index}"
                    )
                    if st.button("Save Name", key=f"save_name_{selected_index}"):
                        chat['display_name'] = new_name
                        with open(user_chat_file, 'w') as f:
                            json.dump(all_chats, f, indent=2)
                        st.success("Chat renamed!")
                        st.rerun()
                
                # Display the selected chat
                with st.expander(f"🗒️ {chat_names[selected_index]}"):
                    for msg in chat['messages']:
                        st.chat_message(msg['role']).markdown(msg['content'])
                    
                    st.markdown("**Trait Snapshot:**")
                    fig, ax = plt.subplots(figsize=(8, 4))
                    ax.barh(
                        list(chat['traits'].keys()),
                        list(chat['traits'].values()),
                        color="#6eb5ff"
                    )
                    ax.invert_yaxis()
                    st.pyplot(fig)
                    
                    # Show original timestamp in small text
                    st.caption(f"Originally saved: {chat['timestamp']}")
        except Exception as e:
            st.error(f"Error loading saved chats: {e}")
    else:
        st.info("No chats saved yet.")