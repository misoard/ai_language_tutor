import streamlit as st
from utils import storage
from sidebar import render_sidebar 
import json
import re
import openai

st.set_page_config(page_title="Lesson Plan", page_icon="📚", layout="wide")
render_sidebar()

# --- Load Configuration from config.json ---
with open('utils/config.json', 'r') as config_file:
    config = json.load(config_file)

# Extract parameters from config
OPENAI_MODEL = config.get('openai_model_name', 'gpt-4o')
TEMPERATURE = config.get('temperature', 0.7)
LANGUAGE = config.get('language', 'English')

# --- 🛠️ Initialize Lesson Plan and User Inputs in Session State ---
if "lesson_plan" not in st.session_state:
    st.session_state.lesson_plan = storage.load_lesson_plan()

if "lesson_plan_inputs" not in st.session_state:
    # Load saved inputs or initialize defaults
    saved_inputs = storage.load_lesson_plan_inputs()  # Implement this in storage
    st.session_state.lesson_plan_inputs = saved_inputs or {
        "user_level": "Beginner",
        "learning_period": "1 Month",
        "user_goals": ""
    }

# --- 📚 Lesson Plan Section ---
st.title("📚 Lesson Plan")
st.write("You can edit your plan by removing or adding items. Press 'Practice' to start lesson on the selected topic.")
st.write("Track your progress by crossing out the topics that you have already learned. Generate a new plan once your goals have changed.")


with st.sidebar:
    st.header("📚 Generate a Lesson Plan")

    # Pre-fill input fields with saved values
    user_level = st.selectbox(
        "Select your level:",
        ["Beginner", "Intermediate", "Advanced"],
        index=["Beginner", "Intermediate", "Advanced"].index(st.session_state.lesson_plan_inputs["user_level"])
    )

    learning_period = st.selectbox(
        "Study duration:",
        ["1 Week", "1 Month", "3 Months"],
        index=["1 Week", "1 Month", "3 Months"].index(st.session_state.lesson_plan_inputs["learning_period"])
    )

    user_goals = st.text_area(
        "Your learning goals:",
        value=st.session_state.lesson_plan_inputs["user_goals"]
    )

    if st.button("📜 Generate Lesson Plan"):
        # Save user inputs to session state and storage
        st.session_state.lesson_plan_inputs = {
            "user_level": user_level,
            "learning_period": learning_period,
            "user_goals": user_goals
        }
        storage.save_lesson_plan_inputs(st.session_state.lesson_plan_inputs)  # Implement in storage

        # OpenAI API Call to Generate Lesson Plan
        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

        lesson_prompt = f"""
        You are an AI that generates structured **lesson plans** for learning {LANGUAGE}.
        - The user is at **{user_level}** level.
        - The lesson plan duration is **{learning_period}**.
        - The learning goals are: "{user_goals}".

        **Format:**
        - Output **only JSON** (no extra text, no explanations).
        - Use this exact JSON format:
        ```json
        {{
            "lesson_plan": {{
                "Week 1 - Meeting new people": ["Introduce yourself, your occupation and hobbies", "Role play: meeting new people", "Describe your day"],
                "Week 2 - Travel and transport": ["Buying tickets, asking for directions", "Describe your latest journey", "Conversation at a hotel, at a railway station"],
                "Week 3 - Home, family and friends": ["Describe your apartment", "Describe your friends and family members", "Inviting guests"]
            }}
        }}
        ```
        - If **duration is less than 2 weeks**, use `"Day X - Topic"` format.
        - If **duration is 2 weeks or more**, use `"Week X - Topic"` format.
        - Each day/week must have **at least 2 tasks**.
        - **Return only valid JSON**.
        """

        with st.spinner("Generating lesson plan..."):
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You generate structured JSON lesson plans only."},
                    {"role": "user", "content": lesson_prompt}
                ],
                temperature=TEMPERATURE
            )

        # Extract JSON from response safely
        json_match = re.search(r'\{.*\}', response.choices[0].message.content, re.DOTALL)

        if json_match:
            try:
                lesson_plan_json = json.loads(json_match.group())

                if "lesson_plan" in lesson_plan_json:
                    # Convert JSON into structured lesson format
                    formatted_plan = [
                        {"week_or_day": key, "assignments": [{"title": task, "completed": False} for task in value]}
                        for key, value in lesson_plan_json["lesson_plan"].items()
                    ]

                    # Save lesson plan
                    st.session_state.lesson_plan = formatted_plan
                    storage.save_lesson_plan(st.session_state.lesson_plan)
                    st.rerun()
                else:
                    st.error("Error: AI response did not include 'lesson_plan' key. Try again.")
            except json.JSONDecodeError:
                st.error("Error: AI response was not valid JSON. Try again.")
        else:
            st.error("Error: AI did not return JSON. Please try again.")

# --- Practice Dialog ---
if st.session_state.get("practice_dialog", {}).get("show", False):
    dialog = st.session_state.practice_dialog
    
    st.warning("⚠️ You have an in-progress session for this assignment.")
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("▶️ Continue Session", type="primary"):
            st.session_state.start_session_data = {
                "action": "continue",
                "session_id": dialog["existing_session_id"]
            }
            st.session_state.practice_dialog = {"show": False}
            st.switch_page("pages/chatbot.py")
    
    with col2:
        if st.button("🔄 Start New Session"):
            st.session_state.start_session_data = {
                "action": "new",
                "lesson_key": dialog["lesson_key"],
                "assignment": dialog["assignment"]
            }
            st.session_state.practice_dialog = {"show": False}
            st.switch_page("pages/chatbot.py")
    
    with col3:
        if st.button("❌ Cancel"):
            st.session_state.practice_dialog = {"show": False}
            st.rerun()
    
    st.markdown("---")

# --- 📝 Display and Manage Lesson Plan ---
if not st.session_state.lesson_plan:
    st.warning("No lesson plan available. Generate one from the sidebar!")
else:
    corrected_plan = []
    for entry in st.session_state.lesson_plan:
        if isinstance(entry, dict) and "week_or_day" in entry and "assignments" in entry:
            corrected_plan.append(entry)

    # Save corrected format
    if corrected_plan != st.session_state.lesson_plan:
        st.session_state.lesson_plan = corrected_plan
        storage.save_lesson_plan(st.session_state.lesson_plan)

    # Display lessons and assignments
    for i, lesson in enumerate(st.session_state.lesson_plan):
        st.markdown(f"### 🔹 {lesson['week_or_day']}")

        for j, assignment in enumerate(lesson["assignments"]):
            col1, col2, col3 = st.columns([0.7, 0.15, 0.15])

            # Task with completion checkbox
            with col1:
                completed = st.checkbox(
                    assignment["title"],
                    assignment["completed"],
                    key=f"lesson_{i}_assignment_{j}"
                )

                # Update completion status
                if completed != assignment["completed"]:
                    st.session_state.lesson_plan[i]["assignments"][j]["completed"] = completed
                    storage.save_lesson_plan(st.session_state.lesson_plan)
                    
                    # If marking as completed, check if there's an active session to end
                    if completed:
                        session = storage.get_session_by_assignment(lesson["week_or_day"], assignment["title"])
                        if session and session["status"] == "in_progress":
                            # Auto-trigger session end (user will need to confirm in chatbot)
                            st.info(f"💡 Assignment completed! Remember to end the session in the chatbot.")

            # Play button to practice this item
            with col2:
                if st.button("▶️ Practice", key=f"play_{i}_{j}"):
                    # Check if there's an existing session for this assignment
                    existing_session = storage.get_session_by_assignment(
                        lesson["week_or_day"], 
                        assignment["title"]
                    )
                    
                    if existing_session:
                        # Show dialog to continue or start new
                        st.session_state.practice_dialog = {
                            "show": True,
                            "lesson_key": lesson["week_or_day"],
                            "assignment": assignment["title"],
                            "existing_session_id": existing_session["session_id"]
                        }
                        st.rerun()
                    else:
                        # No existing session, create new one
                        st.session_state.start_session_data = {
                            "action": "new",
                            "lesson_key": lesson["week_or_day"],
                            "assignment": assignment["title"]
                        }
                        st.switch_page("pages/chatbot.py")

            # Delete button to remove task
            with col3:
                if st.button("❌", key=f"delete_{i}_{j}"):
                    del st.session_state.lesson_plan[i]["assignments"][j]
                    storage.save_lesson_plan(st.session_state.lesson_plan)
                    st.rerun()

        # Add a new assignment under each week/day
        new_task = st.text_input(f"➕ Add task for {lesson['week_or_day']}", key=f"new_task_{i}")
        if st.button(f"Add to {lesson['week_or_day']}", key=f"add_task_{i}"):
            if new_task.strip():
                st.session_state.lesson_plan[i]["assignments"].append({"title": new_task.strip(), "completed": False})
                storage.save_lesson_plan(st.session_state.lesson_plan)
                st.rerun()
