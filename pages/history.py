import streamlit as st
import json
from datetime import datetime
from sidebar import render_sidebar
from utils import storage

st.set_page_config(page_title="Lesson History", page_icon="📜")
st.title("📜 Lesson History")
st.write("Review your completed sessions and practice history.")
render_sidebar()
st.sidebar.header("📜 History of your lessons")

# --- Tabs for different views ---
tab1, tab2, tab3 = st.tabs(["📚 Session Summaries", "💬 Free Chat History", "📊 All Messages"])

# --- Tab 1: Session Summaries ---
with tab1:
    st.subheader("Session Summaries")
    
    completed_sessions = storage.get_completed_sessions()
    in_progress_sessions = storage.get_in_progress_sessions()
    
    if not completed_sessions and not in_progress_sessions:
        st.info("No sessions yet. Start practicing from the Lesson Plan!")
    else:
        # In-progress sessions
        if in_progress_sessions:
            st.markdown("### 🟢 In Progress")
            for session in in_progress_sessions:
                with st.expander(f"📝 {session['assignment']} ({session['lesson_key']})"):
                    start_time = datetime.fromisoformat(session["start_time"]).strftime("%B %d, %Y at %I:%M %p")
                    st.markdown(f"**Started:** {start_time}")
                    st.markdown(f"**Status:** In Progress")
                    
                    # Show messages
                    messages = storage.get_messages_by_session(session["session_id"])
                    if messages:
                        st.markdown(f"**Messages:** {len(messages)}")
                        if st.button(f"View Messages", key=f"view_in_progress_{session['session_id']}"):
                            st.markdown("---")
                            for msg in messages:
                                role = "👤 User" if msg["role"] == "user" else "🤖 Assistant"
                                st.markdown(f"**{role}:** {msg['content']}")
        
        # Completed sessions
        if completed_sessions:
            st.markdown("### ✅ Completed Sessions")
            for session in sorted(completed_sessions, key=lambda x: x["end_time"], reverse=True):
                with st.expander(f"✓ {session['assignment']} ({session['lesson_key']})"):
                    start_time = datetime.fromisoformat(session["start_time"]).strftime("%B %d, %Y at %I:%M %p")
                    end_time = datetime.fromisoformat(session["end_time"]).strftime("%B %d, %Y at %I:%M %p")
                    
                    st.markdown(f"**Started:** {start_time}")
                    st.markdown(f"**Completed:** {end_time}")
                    st.markdown(f"**Messages:** {session['message_count']}")
                    
                    st.markdown("---")
                    st.markdown(f"**📝 Summary:** {session['summary']}")
                    
                    if session['what_worked']:
                        st.markdown(f"**✨ What Worked:** {session['what_worked']}")
                    
                    if session['understood']:
                        st.markdown(f"**✓ Understood:** {session['understood']}")
                    
                    if session['difficulties']:
                        st.markdown(f"**⚠️ Difficulties:** {session['difficulties']}")
                    
                    if session['common_mistakes']:
                        st.markdown(f"**❌ Common Mistakes:**")
                        for mistake in session['common_mistakes']:
                            st.markdown(f"  - {mistake}")
                    
                    # Show messages
                    if st.button(f"View Full Conversation", key=f"view_completed_{session['session_id']}"):
                        st.markdown("---")
                        messages = storage.get_messages_by_session(session["session_id"])
                        for msg in messages:
                            role = "👤 User" if msg["role"] == "user" else "🤖 Assistant"
                            st.markdown(f"**{role}:** {msg['content']}")

# --- Tab 2: Free Chat History ---
with tab2:
    st.subheader("Free Chat (No Session)")
    
    # Get messages without session_id
    chat_history = storage.load_chat_history()
    free_chat_messages = [msg for msg in chat_history if not msg.get("session_id")]
    
    if not free_chat_messages:
        st.info("No free chat messages yet.")
    else:
        # Group by date
        history_by_date = {}
        for msg in free_chat_messages:
            try:
                msg_time = datetime.strptime(msg["timestamp"][:19], "%Y-%m-%dT%H:%M:%S")
                date_str = msg_time.strftime("%Y-%m-%d")
                
                if date_str not in history_by_date:
                    history_by_date[date_str] = []
                history_by_date[date_str].append(msg)
            except (ValueError, KeyError):
                pass
        
        # Display by date
        for date, messages in sorted(history_by_date.items(), reverse=True):
            with st.expander(f"📅 {date} ({len(messages)} messages)"):
                for msg in messages:
                    role = "👤 User" if msg["role"] == "user" else "🤖 Assistant"
                    st.markdown(f"**{role}:** {msg['content']}")

# --- Tab 3: All Messages ---
with tab3:
    st.subheader("All Messages")
    
    chat_history = storage.load_chat_history()
    
    if not chat_history:
        st.info("No messages yet.")
    else:
        # Group by date
        history_by_date = {}
        for msg in chat_history:
            try:
                msg_time = datetime.strptime(msg["timestamp"][:19], "%Y-%m-%dT%H:%M:%S")
                date_str = msg_time.strftime("%Y-%m-%d")
                
                if date_str not in history_by_date:
                    history_by_date[date_str] = []
                history_by_date[date_str].append(msg)
            except (ValueError, KeyError):
                pass
        
        # Display by date
        for date, messages in sorted(history_by_date.items(), reverse=True):
            with st.expander(f"📅 {date} ({len(messages)} messages)"):
                for msg in messages:
                    role = "👤 User" if msg["role"] == "user" else "🤖 Assistant"
                    session_info = f" [Session: {msg.get('session_id', 'Free chat')}]" if msg.get('session_id') else " [Free chat]"
                    st.markdown(f"**{role}**{session_info}: {msg['content']}")
