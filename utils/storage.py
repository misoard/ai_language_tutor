import json
import streamlit as st
import uuid
from datetime import datetime

VOCAB_FILE = "assets/user_vocabulary.json"
LESSON_PLAN_FILE = "assets/lesson_plan.json"
USER_INPUTS_FILE = "assets/lesson_plan_inputs.json"
CHAT_HISTORY_FILE = "assets/chat_history.json"
SESSION_SUMMARIES_FILE = "assets/session_summaries.json"

def save_lesson_plan_inputs(inputs):
    with open(USER_INPUTS_FILE, "w") as f:
        json.dump(inputs, f)

def load_lesson_plan_inputs():
    try:
        with open(USER_INPUTS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def load_vocabulary():
    try:
        with open(VOCAB_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_vocabulary(vocab_list):
    with open(VOCAB_FILE, "w") as f:
        json.dump(vocab_list, f)

def load_lesson_plan():
    try:
        with open(LESSON_PLAN_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_lesson_plan(plan):
    with open(LESSON_PLAN_FILE, "w") as f:
        json.dump(plan, f)

# --- Function to load chat history from file ---
def load_chat_history():
    try:
        with open(CHAT_HISTORY_FILE, "r") as f:
            messages = json.load(f)
            
            # Migrate old messages to include session_id field
            migrated = False
            for msg in messages:
                if "session_id" not in msg:
                    msg["session_id"] = None
                    migrated = True
            
            # Save migrated messages back
            if migrated:
                save_chat_history(messages)
            
            return messages
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# --- Function to save chat history to file ---
def save_chat_history(messages):
    try:
        with open(CHAT_HISTORY_FILE, "w") as f:
            json.dump(messages, f)
    except Exception as e:
        st.error(f"Error saving chat history: {e}")

# --- Session Management Functions ---

def load_sessions():
    """Load all session summaries"""
    try:
        with open(SESSION_SUMMARIES_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_sessions(sessions):
    """Save all session summaries"""
    try:
        with open(SESSION_SUMMARIES_FILE, "w") as f:
            json.dump(sessions, f, indent=2)
    except Exception as e:
        st.error(f"Error saving sessions: {e}")

def create_session(lesson_key, assignment):
    """Create a new session and return its ID"""
    sessions = load_sessions()
    session_id = str(uuid.uuid4())
    new_session = {
        "session_id": session_id,
        "lesson_key": lesson_key,
        "assignment": assignment,
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "message_count": 0,
        "summary": None,
        "what_worked": None,
        "understood": None,
        "difficulties": None,
        "common_mistakes": [],
        "pdf_path": None,
        "status": "in_progress"
    }
    sessions.append(new_session)
    save_sessions(sessions)
    return session_id

def get_session(session_id):
    """Get a specific session by ID"""
    sessions = load_sessions()
    for session in sessions:
        if session["session_id"] == session_id:
            return session
    return None

def update_session(session_id, updates):
    """Update specific fields of a session"""
    sessions = load_sessions()
    for i, session in enumerate(sessions):
        if session["session_id"] == session_id:
            sessions[i].update(updates)
            save_sessions(sessions)
            return True
    return False

def get_session_by_assignment(lesson_key, assignment):
    """Find an in-progress session for a specific assignment"""
    sessions = load_sessions()
    for session in sessions:
        if (session["lesson_key"] == lesson_key and 
            session["assignment"] == assignment and 
            session["status"] == "in_progress"):
            return session
    return None

def get_in_progress_sessions():
    """Get all in-progress sessions"""
    sessions = load_sessions()
    return [s for s in sessions if s["status"] == "in_progress"]

def get_completed_sessions():
    """Get all completed sessions"""
    sessions = load_sessions()
    return [s for s in sessions if s["status"] == "completed"]

def complete_session(session_id, summary_data):
    """Mark session as completed and save summary"""
    updates = {
        "status": "completed",
        "end_time": datetime.now().isoformat(),
        "summary": summary_data.get("summary"),
        "what_worked": summary_data.get("what_worked"),
        "understood": summary_data.get("understood"),
        "difficulties": summary_data.get("difficulties"),
        "common_mistakes": summary_data.get("common_mistakes", [])
    }
    return update_session(session_id, updates)

def get_messages_by_session(session_id):
    """Get all messages for a specific session"""
    chat_history = load_chat_history()
    return [msg for msg in chat_history if msg.get("session_id") == session_id]

def get_recent_messages(session_id, limit=20):
    """Get the most recent N messages for a session"""
    messages = get_messages_by_session(session_id)
    return messages[-limit:] if len(messages) > limit else messages

def get_all_summaries():
    """Get all completed session summaries as a formatted string for context"""
    completed = get_completed_sessions()
    if not completed:
        return ""
    
    summaries_text = "\n\n=== Previous Session Summaries ===\n"
    for session in completed:
        summaries_text += f"\n**Session: {session['assignment']}** ({session['lesson_key']})\n"
        summaries_text += f"Summary: {session['summary']}\n"
        if session['difficulties']:
            summaries_text += f"Difficulties: {session['difficulties']}\n"
        if session['common_mistakes']:
            summaries_text += f"Common mistakes: {', '.join(session['common_mistakes'])}\n"
    
    return summaries_text
