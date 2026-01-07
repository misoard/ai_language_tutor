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
tab1, tab2, tab3, tab4 = st.tabs(["📚 Session Summaries", "📄 PDF Session Summaries", "💬 Free Chat History", "📊 All Messages"])

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
                    
                    st.markdown("---")
                    
                    # HTML Summary Download Button
                    if session.get('pdf_path'):
                        import os
                        if os.path.exists(session['pdf_path']):
                            with open(session['pdf_path'], "r", encoding="utf-8") as html_file:
                                html_content = html_file.read()
                                st.download_button(
                                    label="📄 Download HTML Summary",
                                    data=html_content,
                                    file_name=session['pdf_path'].split("/")[-1],
                                    mime="text/html",
                                    key=f"download_html_{session['session_id']}"
                                )
                                st.caption("💡 Open HTML in browser and print/save as PDF")
                        else:
                            st.warning("Summary file not found")
                    else:
                        st.info("No summary available for this session")
                    
                    # Show messages
                    if st.button(f"View Full Conversation", key=f"view_completed_{session['session_id']}"):
                        st.markdown("---")
                        messages = storage.get_messages_by_session(session["session_id"])
                        for msg in messages:
                            role = "👤 User" if msg["role"] == "user" else "🤖 Assistant"
                            st.markdown(f"**{role}:** {msg['content']}")

# --- Tab 2: PDF Session Summaries (HTML Display) ---
with tab2:
    st.subheader("PDF Session Summaries")
    
    # Get both completed and in-progress sessions that have HTML files
    all_sessions = storage.get_completed_sessions() + storage.get_in_progress_sessions()
    sessions_with_html = [s for s in all_sessions if s.get('pdf_path')]
    
    # Also scan for free chat HTML files
    import os
    import glob
    pdf_dir = "assets/pdfs"
    free_chat_files = []
    if os.path.exists(pdf_dir):
        free_chat_pattern = os.path.join(pdf_dir, "free_chat_*.html")
        for filepath in glob.glob(free_chat_pattern):
            # Extract timestamp from filename
            filename = os.path.basename(filepath)
            timestamp_str = filename.replace("free_chat_", "").replace(".html", "")
            try:
                # Parse timestamp: YYYYMMDD_HHMMSS
                file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                free_chat_files.append({
                    "type": "free_chat",
                    "path": filepath,
                    "timestamp": file_time,
                    "display_name": f"Free Chat - {file_time.strftime('%B %d, %Y at %I:%M %p')}"
                })
            except:
                pass
    
    # Combine sessions and free chats
    all_items = sessions_with_html + free_chat_files
    
    if not all_items:
        st.info("No summaries yet. Generate one from the chatbot!")
    else:
        # Let user select a session or free chat
        item_options = []
        for item in all_items:
            if item.get('type') == 'free_chat':
                item_options.append(item['display_name'])
            else:
                item_options.append(f"{item['lesson_key']} - {item['assignment']} ({item['status'].title()})")
        
        selected_idx = st.selectbox(
            "Select a session to view:",
            range(len(item_options)),
            format_func=lambda i: item_options[i]
        )
        
        selected_item = all_items[selected_idx]
        
        # Display HTML if available
        html_path = selected_item.get('pdf_path') or selected_item.get('path')
        
        if html_path and os.path.exists(html_path):
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Display the HTML in an iframe or use components.html
            import streamlit.components.v1 as components
            components.html(html_content, height=800, scrolling=True)
            
            # Download button
            st.download_button(
                label="⬇️ Download HTML Summary",
                data=html_content,
                file_name=os.path.basename(html_path),
                mime="text/html"
            )
            st.caption("💡 Download and open in browser, then print/save as PDF")
        else:
            st.warning("Summary file not found. Generate it from the chatbot.")

# --- Tab 3: Free Chat History ---
with tab3:
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

# --- Tab 4: All Messages ---
with tab4:
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
