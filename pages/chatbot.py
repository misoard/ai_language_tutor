import streamlit as st
from utils import storage
from sidebar import render_sidebar
import openai
import random
import json

st.set_page_config(page_title="Let's talk", page_icon="💬", layout="wide")

# --- 💬 Chatbot Section ---
st.title("💬 Let's Talk")
st.write("Talk to your AI teaching assistant on any topic, ask for explanations of rules, useful vocabulary, or exercises.")
st.write("Save any new words to your vocabulary list in the side panel.")
st.write("Press 'Quiz!' to get exercises for practicing random words from your vocabulary list.")

# --- Load Configuration from config.json ---
with open('utils/config.json', 'r') as config_file:
    config = json.load(config_file)

# Extract parameters from config
OPENAI_MODEL = config.get('openai_model_name', 'gpt-4o')
TEMPERATURE = config.get('temperature', 0.7)
LANGUAGE = config.get('language', 'English')

# AI Response Function from the whole history
def get_ai_response_history(messages):
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    # Include system prompt if available
    full_messages = [st.session_state.get("system_prompt")] if "system_prompt" in st.session_state else []
    full_messages.extend(messages)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=full_messages,
        temperature=TEMPERATURE
    )
    return response.choices[0].message.content

# --- Load user level and goals ---
lesson_plan_inputs = storage.load_lesson_plan_inputs()
user_level = lesson_plan_inputs.get("user_level", "Beginner") if lesson_plan_inputs else "Beginner"
user_goals = lesson_plan_inputs.get("user_goals", "") if lesson_plan_inputs else ""

# --- Get all previous session summaries for context ---
session_summaries_context = storage.get_all_summaries()

# --- Initialize session state for messages if not present ---
if "messages" not in st.session_state:
    st.session_state.system_prompt = {"role": "system", "content": f"""
        You are a friendly personal {LANGUAGE} language tutor, helping to improve speaking skills.
        
        **Student Profile:**
        - Current level: {user_level}
        - Learning goals: {user_goals if user_goals else "General language improvement"}
        
        {session_summaries_context}
        
        **Your role:**
        - Speak only in {LANGUAGE}, but provide translations if requested.
        - Plan lesson topics covering everyday situations, professional settings, and cultural aspects of {LANGUAGE} speaking countries.
        - Provide a list of key words and phrases for each topic, along with examples of usage.
        - Check user's answers to questions, correct mistakes, and explain grammar and pronunciation nuances. When correcting mistakes, you strike out incorrect words and write the correct ones in bold next to them, so the user can see errors. In the case of grammar mistakes, you remind the user of the relevant rule.
        - Keep the conversation going, ask guiding questions, engage the user in dialogues, and help them develop fluency.
        - Suggest more advanced vocabulary based on responses, ask follow-up questions, and encourage the user to use new words in context.
        - Maintain a vocabulary list of new words and occasionally remind the user to use them in conversation.
        - Recommend additional materials: movies, books, podcasts, and articles in {LANGUAGE}.
        - Encourage the user to think in {LANGUAGE} and not be afraid of mistakes, creating a friendly and motivating learning environment.
        - When practicing a specific assignment, monitor progress and suggest ending the session with a final test when you think the goals have been achieved.
        """}

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Initialize current session ID if not present ---
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None

# --- Handle session creation/continuation from lesson plan ---
if "start_session_data" in st.session_state and st.session_state.start_session_data:
    session_data = st.session_state.start_session_data
    
    if session_data["action"] == "new":
        # Create new session
        session_id = storage.create_session(session_data["lesson_key"], session_data["assignment"])
        st.session_state.current_session_id = session_id
        st.session_state.messages = []
        
        # Add preset message
        preset_message = f"Let's practice {session_data['assignment']}"
        from datetime import datetime
        st.session_state.messages.append({
            "role": "user", 
            "content": preset_message,
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id
        })
        
        # Get AI response
        with st.spinner("Starting practice..."):
            bot_reply = get_ai_response_history(st.session_state.messages)
            st.session_state.messages.append({
                "role": "assistant", 
                "content": bot_reply,
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id
            })
        
        # Save to chat history
        chat_history = storage.load_chat_history()
        chat_history.extend(st.session_state.messages)
        storage.save_chat_history(chat_history)
        
    elif session_data["action"] == "continue":
        # Load existing session
        st.session_state.current_session_id = session_data["session_id"]
        # Load last 20 messages from this session
        st.session_state.messages = storage.get_recent_messages(session_data["session_id"], limit=20)
    
    # Clear the session data
    st.session_state.start_session_data = None
    st.rerun()

# --- 📖 Vocabulary Panel ---
render_sidebar()
st.sidebar.header("💬 Your Teaching Assistant")

# --- Display Current Session ---
if st.session_state.current_session_id:
    current_session = storage.get_session(st.session_state.current_session_id)
    if current_session:
        from datetime import datetime
        start_time = datetime.fromisoformat(current_session["start_time"]).strftime("%b %d, %I:%M %p")
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📚 Current Session")
        st.sidebar.markdown(f"**{current_session['lesson_key']}**")
        st.sidebar.markdown(f"📝 {current_session['assignment']}")
        st.sidebar.markdown(f"🕐 Started: {start_time}")
        st.sidebar.markdown(f"Status: 🟢 In Progress")
        st.sidebar.markdown("---")

# --- Session Browser ---
st.sidebar.markdown("### 📖 All Sessions")

in_progress_sessions = storage.get_in_progress_sessions()
completed_sessions = storage.get_completed_sessions()

if in_progress_sessions:
    with st.sidebar.expander(f"🟢 In Progress ({len(in_progress_sessions)})", expanded=False):
        for session in in_progress_sessions:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{session['assignment']}**")
                st.caption(session['lesson_key'])
            with col2:
                if st.button("▶️", key=f"continue_{session['session_id']}", help="Continue"):
                    st.session_state.start_session_data = {
                        "action": "continue",
                        "session_id": session["session_id"]
                    }
                    st.rerun()

if completed_sessions:
    with st.sidebar.expander(f"✅ Completed ({len(completed_sessions)})", expanded=False):
        for session in completed_sessions:
            st.markdown(f"**{session['assignment']}**")
            st.caption(session['lesson_key'])
            if st.button("👁️ View", key=f"view_{session['session_id']}", help="View in History"):
                st.switch_page("pages/history.py")

st.sidebar.markdown("---")

# Load vocabulary list
vocab_list = storage.load_vocabulary()

# Ensure all entries are dictionaries with 'word', 'translation', and 'example'
corrected_vocab_list = []
for entry in vocab_list:
    if isinstance(entry, str):
        corrected_vocab_list.append({
            "word": entry,
            "translation": "None.",
            "example": "None."
        })
    elif isinstance(entry, dict):
        corrected_vocab_list.append({
            "word": entry.get("word", "Unknown"),
            "translation": entry.get("translation", "None."),
            "example": entry.get("example", "None.")
        })

if corrected_vocab_list != vocab_list:
    storage.save_vocabulary(corrected_vocab_list)

vocab_list = corrected_vocab_list

# Display vocabulary in sidebar

# --- Add New Word Section ---
new_word = st.sidebar.text_input("➕ Add a new word", key="new_vocab_word")

if st.sidebar.button("Add Word"):
    if new_word.strip() and all(w["word"] != new_word.strip() for w in vocab_list):
        # Generate translation and example using OpenAI
        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

        prompt = f"""
        You are a {LANGUAGE} language expert. For the word "{new_word}", provide:
        1. A concise translation to English.
        2. One example sentence in {LANGUAGE} using the word.

        Format the response as:
        Translation: <your translation>
        Example: <your example>
        """

        with st.spinner(f"Fetching translation and example for '{new_word}'..."):
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=TEMPERATURE
            )

        # Parse the response
        content = response.choices[0].message.content
        translation = ""
        example = ""

        for line in content.splitlines():
            if line.startswith("Translation:"):
                translation = line.replace("Translation:", "").strip()
            elif line.startswith("Example:"):
                example = line.replace("Example:", "").strip()

        if translation and example:
            # Add word with translation and example
            vocab_list.append({
                "word": new_word.strip(),
                "translation": translation,
                "example": example
            })
            storage.save_vocabulary(vocab_list)
            st.success(f"Added '{new_word}' with translation and example.")
            st.rerun()
        else:
            st.error("Failed to fetch translation and example. Try again.")
if vocab_list:
    for word_entry in vocab_list:
        st.sidebar.markdown(f"- **{word_entry['word']}**")
else:
    st.sidebar.write("No words in your vocabulary.")

# --- 📋 Quiz Button ---
if st.sidebar.button("📝 Quiz!"):
    if len(vocab_list) < 1:
        st.sidebar.warning("Add at least one word to start a quiz.")
    else:
        quiz_words = random.sample(vocab_list, min(10, len(vocab_list)))
        quiz_word_list = [w["word"] for w in quiz_words]

        quiz_prompt = f"""
        You are a {LANGUAGE} language tutor. Create an engaging exercise using these words: {', '.join(quiz_word_list)}.
        Format it as a quiz that the user can answer.
        """

        with st.spinner("Generating quiz..."):
            quiz_response = get_ai_response_history(st.session_state.messages + [{"role": "user", "content": quiz_prompt}])

        from datetime import datetime
        st.session_state.messages.append({
            "role": "assistant", 
            "content": quiz_response,
            "timestamp": datetime.now().isoformat(),
            "session_id": st.session_state.current_session_id
        })
        
        # Save to chat history
        chat_history = storage.load_chat_history()
        chat_history.append(st.session_state.messages[-1])
        storage.save_chat_history(chat_history)

# --- End Session Button ---
if st.session_state.current_session_id:
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("✓ End Session", type="primary"):
            st.session_state.show_end_session_dialog = True
            st.rerun()
    with col2:
        if st.button("🔄 New Free Chat"):
            st.session_state.current_session_id = None
            st.session_state.messages = []
            st.rerun()

# --- End Session Dialog ---
if st.session_state.get("show_end_session_dialog", False):
    with st.form("end_session_form"):
        st.subheader("End Session")
        st.write("Generating session summary...")
        
        # Generate summary using AI
        session = storage.get_session(st.session_state.current_session_id)
        session_messages = storage.get_messages_by_session(st.session_state.current_session_id)
        
        # Create summary prompt
        conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in session_messages])
        
        summary_prompt = f"""
        Analyze this {LANGUAGE} language learning session and provide a detailed summary in JSON format.
        
        Assignment: {session['assignment']}
        Conversation:
        {conversation_text[:4000]}  
        
        Provide your analysis as valid JSON with these exact fields:
        {{
            "summary": "2-3 sentence overview of what was practiced",
            "what_worked": "What the student did well",
            "understood": "Concepts/grammar/vocabulary the student understood",
            "difficulties": "Areas where the student struggled",
            "common_mistakes": ["mistake 1", "mistake 2"]
        }}
        
        Return ONLY valid JSON, no other text.
        """
        
        with st.spinner("Analyzing session..."):
            client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.3
            )
            
            import re
            json_match = re.search(r'\{.*\}', response.choices[0].message.content, re.DOTALL)
            if json_match:
                summary_data = json.loads(json_match.group())
            else:
                summary_data = {
                    "summary": "Session completed",
                    "what_worked": "N/A",
                    "understood": "N/A",
                    "difficulties": "N/A",
                    "common_mistakes": []
                }
        
        # Display summary
        st.markdown(f"**Summary:** {summary_data['summary']}")
        st.markdown(f"**What worked:** {summary_data['what_worked']}")
        st.markdown(f"**Understood:** {summary_data['understood']}")
        st.markdown(f"**Difficulties:** {summary_data['difficulties']}")
        
        confirm = st.form_submit_button("Confirm & End Session")
        cancel = st.form_submit_button("Cancel")
        
        if confirm:
            # Save summary and complete session
            storage.complete_session(st.session_state.current_session_id, summary_data)
            storage.update_session(st.session_state.current_session_id, {"message_count": len(session_messages)})
            
            # Clear session
            st.session_state.current_session_id = None
            st.session_state.messages = []
            st.session_state.show_end_session_dialog = False
            st.success("Session ended and summary saved!")
            st.rerun()
        
        if cancel:
            st.session_state.show_end_session_dialog = False
            st.rerun()

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat interface
user_input = st.chat_input("Type your message...")
if user_input:
    from datetime import datetime
    
    # Add user message with metadata
    user_msg = {
        "role": "user", 
        "content": user_input,
        "timestamp": datetime.now().isoformat(),
        "session_id": st.session_state.current_session_id
    }
    st.session_state.messages.append(user_msg)

    with st.chat_message("user"):
        st.write(user_input)

    with st.spinner("Thinking..."):
        bot_reply = get_ai_response_history(st.session_state.messages)

    with st.chat_message("assistant"):
        st.write(bot_reply)

    # Add assistant message with metadata
    assistant_msg = {
        "role": "assistant", 
        "content": bot_reply,
        "timestamp": datetime.now().isoformat(),
        "session_id": st.session_state.current_session_id
    }
    st.session_state.messages.append(assistant_msg)
    
    # Save both messages to chat history
    chat_history = storage.load_chat_history()
    chat_history.extend([user_msg, assistant_msg])
    storage.save_chat_history(chat_history)
    
    # Check if AI suggests ending session (only if in a session)
    if st.session_state.current_session_id and "end this session" in bot_reply.lower():
        st.info("💡 The AI thinks you've mastered this topic. Consider ending the session!")
        if st.button("End Session Now"):
            st.session_state.show_end_session_dialog = True
            st.rerun()
