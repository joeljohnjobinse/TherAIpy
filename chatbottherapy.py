import streamlit as st
import requests
import random
import re
import matplotlib.pyplot as plt

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant", 
        "content": "Hey! I'm here whenever you feel like talking. What's on your mind?"
    }]

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
    st.session_state.page = "💬 Chat"

st.set_page_config(page_title="TherAIpy", layout="wide")

with st.sidebar:
    st.title("🌿 TherAIpy")
    if st.button("💬 Chat", use_container_width=True):
        st.session_state.page = "💬 Chat"
    if st.button("📊 Your Profile", use_container_width=True):
        st.session_state.page = "📊 Your Profile"
    st.markdown("---")
    if st.button("🧹 Clear Chat", use_container_width=True):
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Hey! I'm here whenever you feel like talking. What's on your mind?"
        }]
        for key in st.session_state.traits:
            st.session_state.traits[key] = 0
        st.experimental_rerun()

selected_page = st.session_state.page

def update_traits(response):
    traits_map = {
        "Empathy": ["understand", "empathize", "feel for", "that sounds hard", "pain"],
        "Self-Awareness": ["aware", "reflect", "realize", "introspect"],
        "Anxiety": ["anxious", "worried", "stressed", "nervous"],
        "Optimism": ["hope", "bright side", "get better", "improve", "believe"],
        "Mood Swings": ["up and down", "mixed feelings", "unstable", "change a lot"],
        "Confidence": ["you can", "capable", "strong", "believe in yourself"]
    }

    for trait, keywords in traits_map.items():
        for word in keywords:
            if re.search(rf"\b{word}\b", response, re.IGNORECASE):
                st.session_state.traits[trait] += 1

if selected_page == "💬 Chat":
    st.title("🧠 TherAIpy")
    st.caption("✨ Your emotional support companion")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("💭 How are you feeling today?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                def get_ai_response():
                    headers = {
                        "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": st.secrets.get("APP_URL", "https://theraipy.streamlit.app"),
                        "X-Title": st.secrets.get("APP_NAME", "TherAIpy")
                    }
                    payload = {
                        "model": "anthropic/claude-3-haiku",
                        "messages": st.session_state.messages,
                        "temperature": 0.7,
                        "max_tokens": 1000
                    }

                    try:
                        response = requests.post("https://openrouter.ai/api/v1/chat/completions",
                                                 headers=headers, json=payload, timeout=20)
                        response.raise_for_status()
                        return response.json()["choices"][0]["message"]["content"]
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        return None

                ai_response = get_ai_response()
                if ai_response:
                    cleaned = ai_response.replace("As an AI", "").replace("As an AI assistant", "").strip()
                    openings = [
                        "🌱 I understand...",
                        "🌟 Let's explore this...",
                        "💫 Your feelings matter...",
                        "🌊 This resonates because..."
                    ]
                    final_response = f"{random.choice(openings)} {cleaned}"
                    st.markdown(final_response)
                    st.session_state.messages.append({"role": "assistant", "content": final_response})
                    update_traits(final_response)
                else:
                    st.error("Sorry, I couldn't process that. Please try again.")

elif selected_page == "📊 Your Profile":
    st.title("📊 Your Emotional Profile")
    st.markdown("Here’s what I’ve picked up about you so far from our conversations:")

    good_traits = ["Empathy", "Self-Awareness", "Optimism", "Confidence"]
    bad_traits = ["Anxiety", "Mood Swings"]

    st.divider()
    st.subheader("✨ About You")
    
    def generate_initial_summary():
        if sum(st.session_state.traits.values()) == 0:
            return "Our conversation is just beginning. As we talk more, I'll understand you better."
        return None

    def generate_ai_summary():
        trait_description = "\n".join([f"{trait}: {score}" for trait, score in st.session_state.traits.items()])
        prompt = f"""Based on these conversation traits:
        {trait_description}
        
        Write a warm, compassionate summary about this person's emotional profile in 3 sentences max. 
        Use "you" language. Be specific to these traits. Skip introductory phrases and go straight to the insights."""
        
        headers = {
            "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "anthropic/claude-3-haiku",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 200
        }

        try:
            response = requests.post("https://openrouter.ai/api/v1/chat/completions",
                                   headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return content.split(":")[-1].strip() if ":" in content else content
        except Exception:
            return None

    if sum(st.session_state.traits.values()) == 0:
        summary = generate_initial_summary()
    else:
        with st.spinner("Reflecting on our conversation..."):
            summary = generate_ai_summary() or "I'm beginning to understand you. Keep sharing your thoughts."

    st.markdown(
        f'<div style="padding:20px; border-radius:10px; margin-bottom:20px; '
        f'background-color:#2e2e2e; color:#f0f2f6; border-left:4px solid #6eb5ff;">'
        f'{summary}'
        f'</div>', 
        unsafe_allow_html=True
    )

    with st.container():
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("✅ Strengths")
            for trait in good_traits:
                score = st.session_state.traits[trait]
                st.markdown(f"- {trait}: {score} points")

        with col2:
            st.subheader("⚠️ Challenges")
            for trait in bad_traits:
                score = st.session_state.traits[trait]
                st.markdown(f"- {trait}: {score} points")

    st.divider()
    st.subheader("📈 Visual Overview")
    fig, ax = plt.subplots()
    ax.barh(list(st.session_state.traits.keys()), st.session_state.traits.values(), color="#6eb5ff")
    ax.set_xlim(0, max(2, max(st.session_state.traits.values()) + 2))
    ax.invert_yaxis()
    ax.set_xlabel("Points accumulated from conversations")
    st.pyplot(fig)