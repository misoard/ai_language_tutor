import json
import openai
import streamlit as st
from datetime import datetime
from utils import storage
import os


def escape_html(text):
    """Escape HTML special characters"""
    if not text:
        return text
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;'))


def save_pdf_json(pdf_data, session_id=None, message_count=0):
    """Save PDF JSON to file for reuse with metadata"""
    json_dir = "assets/pdf_jsons"
    os.makedirs(json_dir, exist_ok=True)
    
    # Add metadata to track when to regenerate
    pdf_data_with_meta = {
        "message_count": message_count,
        "generated_at": datetime.now().isoformat(),
        "data": pdf_data
    }
    
    if session_id:
        filename = f"pdf_data_{session_id}.json"
    else:
        filename = f"pdf_data_freechat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    filepath = os.path.join(json_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(pdf_data_with_meta, f, indent=2, ensure_ascii=False)
    
    return filepath


def load_pdf_json(session_id=None, current_message_count=0):
    """
    Load PDF JSON if it exists and is still valid
    Returns None if needs regeneration
    """
    json_dir = "assets/pdf_jsons"
    
    if session_id:
        filename = f"pdf_data_{session_id}.json"
        filepath = os.path.join(json_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            # Check if it's old format (no metadata)
            if "data" not in cached_data:
                # Old format, needs regeneration
                return None
            
            # Check if message count has changed
            cached_count = cached_data.get("message_count", 0)
            if cached_count != current_message_count:
                # Chat has new messages, needs regeneration
                return None
            
            # Valid cache, return the data
            return cached_data["data"]
    
    return None


def generate_pdf_json(messages, language, session=None):
    """
    Generate detailed JSON structure for PDF using AI
    
    Args:
        messages: List of chat messages
        language: Target language being learned
        session: Session object (if applicable)
    
    Returns:
        dict: Structured JSON with objectives, learnings, improvements
    """
    message_count = len(messages)
    
    # Check if JSON already exists and is still valid (avoid duplicate API calls)
    if session:
        existing_json = load_pdf_json(session['session_id'], message_count)
        if existing_json:
            return existing_json
    
    # Prepare conversation text
    conversation_text = "\n".join([
        f"{msg['role']}: {msg['content'][:500]}" 
        for msg in messages[:50]  # Limit to avoid token overflow
    ])
    
    # Determine if session or free chat
    session_info = ""
    if session:
        session_info = f"""
        This was a focused practice session:
        - Lesson: {session['lesson_key']}
        - Assignment: {session['assignment']}
        """
    else:
        session_info = "This was a free conversation (not tied to a specific lesson)."
    
    prompt = f"""
    Analyze this {language} language learning conversation and create a comprehensive summary for a review document.
    
    {session_info}
    
    Conversation:
    {conversation_text}
    
    Generate a detailed JSON summary with these exact fields:
    {{
        "objectives": "What were the main goals/topics of this conversation? (2-3 sentences)",
        "learnings": {{
            "grammar_points": ["Grammar rule 1", "Grammar rule 2"],
            "vocabulary": ["word 1: definition", "word 2: definition"],
            "structures": ["Structure/pattern 1", "Structure/pattern 2"],
            "key_concepts": ["Concept 1", "Concept 2"]
        }},
        "improvements": {{
            "areas_to_focus": ["Area 1", "Area 2"],
            "common_mistakes": ["Mistake 1 with explanation", "Mistake 2 with explanation"],
            "recommendations": ["Recommendation 1", "Recommendation 2"]
        }}
    }}
    
    Be specific and detailed. Include actual examples from the conversation.
    Return ONLY valid JSON, no other text.
    """
    
    # Load config for model settings
    with open('utils/config.json', 'r') as f:
        config = json.load(f)
    
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=config.get('openai_model_name', 'gpt-4o'),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    # Extract JSON
    import re
    json_match = re.search(r'\{.*\}', response.choices[0].message.content, re.DOTALL)
    
    if json_match:
        pdf_data = json.loads(json_match.group())
    else:
        # Fallback structure
        pdf_data = {
            "objectives": "Practice conversation completed",
            "learnings": {
                "grammar_points": [],
                "vocabulary": [],
                "structures": [],
                "key_concepts": []
            },
            "improvements": {
                "areas_to_focus": [],
                "common_mistakes": [],
                "recommendations": []
            }
        }
    
    # Save JSON for reuse with message count
    if session:
        save_pdf_json(pdf_data, session['session_id'], message_count)
    else:
        save_pdf_json(pdf_data, message_count=message_count)
    
    return pdf_data


def create_html_summary(pdf_data, session=None, language="English"):
    """
    Create beautiful HTML summary that can be printed as PDF
    
    Args:
        pdf_data: JSON structure with objectives, learnings, improvements
        session: Session object (if applicable)
        language: Target language
    
    Returns:
        str: Complete HTML document
    """
    # Metadata
    if session:
        title = f"{session['lesson_key']} - {session['assignment']}"
        lesson_info = f"""
        <div class="metadata">
            <p><strong>Lesson:</strong> {escape_html(session['lesson_key'])}</p>
            <p><strong>Assignment:</strong> {escape_html(session['assignment'])}</p>
            <p><strong>Date:</strong> {datetime.fromisoformat(session['start_time']).strftime('%B %d, %Y at %I:%M %p')}</p>
            {f"<p><strong>Completed:</strong> {datetime.fromisoformat(session['end_time']).strftime('%B %d, %Y at %I:%M %p')}</p>" if session.get('end_time') else ""}
        </div>
        """
    else:
        title = "Free Conversation"
        lesson_info = f"""
        <div class="metadata">
            <p><strong>Type:</strong> Free Conversation</p>
            <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        </div>
        """
    
    # Get data
    objectives = escape_html(pdf_data.get('objectives', 'N/A'))
    learnings = pdf_data.get('learnings', {})
    improvements = pdf_data.get('improvements', {})
    
    # Build HTML
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{escape_html(title)} - Summary</title>
    <style>
        @media print {{
            @page {{ margin: 1in; }}
            .no-print {{ display: none; }}
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}
        h2 {{
            color: #2c3e50;
            background: #ecf0f1;
            padding: 10px 15px;
            border-left: 4px solid #3498db;
            margin-top: 30px;
        }}
        h3 {{
            color: #34495e;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        .metadata {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 30px;
        }}
        .metadata p {{
            margin: 5px 0;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        ul {{
            list-style-type: none;
            padding-left: 0;
        }}
        li {{
            padding: 8px 0;
            padding-left: 25px;
            position: relative;
        }}
        li:before {{
            content: "→";
            position: absolute;
            left: 0;
            color: #3498db;
            font-weight: bold;
        }}
        .no-items {{
            font-style: italic;
            color: #7f8c8d;
        }}
        .print-button {{
            background: #3498db;
            color: white;
            border: none;
            padding: 12px 24px;
            font-size: 16px;
            border-radius: 5px;
            cursor: pointer;
            margin-bottom: 20px;
        }}
        .print-button:hover {{
            background: #2980b9;
        }}
    </style>
</head>
<body>
    <button class="print-button no-print" onclick="window.print()">🖨️ Print / Save as PDF</button>
    
    <div class="container">
        <h1>{escape_html(language)} Learning Session Summary</h1>
        
        {lesson_info}
        
        <div class="section">
            <h2>1. Objectives</h2>
            <p>{objectives}</p>
        </div>
        
        <div class="section">
            <h2>2. What Was Learned</h2>
            
            <h3>Grammar Points</h3>
            {"<ul>" + "".join([f"<li>{escape_html(item)}</li>" for item in learnings.get('grammar_points', [])]) + "</ul>" if learnings.get('grammar_points') else '<p class="no-items">None recorded</p>'}
            
            <h3>Vocabulary</h3>
            {"<ul>" + "".join([f"<li>{escape_html(item)}</li>" for item in learnings.get('vocabulary', [])]) + "</ul>" if learnings.get('vocabulary') else '<p class="no-items">None recorded</p>'}
            
            <h3>Structures & Patterns</h3>
            {"<ul>" + "".join([f"<li>{escape_html(item)}</li>" for item in learnings.get('structures', [])]) + "</ul>" if learnings.get('structures') else '<p class="no-items">None recorded</p>'}
            
            <h3>Key Concepts</h3>
            {"<ul>" + "".join([f"<li>{escape_html(item)}</li>" for item in learnings.get('key_concepts', [])]) + "</ul>" if learnings.get('key_concepts') else '<p class="no-items">None recorded</p>'}
        </div>
        
        <div class="section">
            <h2>3. Areas for Improvement</h2>
            
            <h3>Focus Areas</h3>
            {"<ul>" + "".join([f"<li>{escape_html(item)}</li>" for item in improvements.get('areas_to_focus', [])]) + "</ul>" if improvements.get('areas_to_focus') else '<p class="no-items">None recorded</p>'}
            
            <h3>Common Mistakes</h3>
            {"<ul>" + "".join([f"<li>{escape_html(item)}</li>" for item in improvements.get('common_mistakes', [])]) + "</ul>" if improvements.get('common_mistakes') else '<p class="no-items">None recorded</p>'}
            
            <h3>Recommendations</h3>
            {"<ul>" + "".join([f"<li>{escape_html(item)}</li>" for item in improvements.get('recommendations', [])]) + "</ul>" if improvements.get('recommendations') else '<p class="no-items">None recorded</p>'}
        </div>
    </div>
</body>
</html>
    """
    
    return html


def create_html_from_json(pdf_data, session=None, is_free_chat=False):
    """
    Create HTML summary file (can be printed as PDF)
    
    Args:
        pdf_data: JSON structure with objectives, learnings, improvements
        session: Session object (if applicable)
        is_free_chat: Boolean indicating if this is free chat
    
    Returns:
        str: Path to generated HTML file
    """
    
    # Load config for language
    with open('utils/config.json', 'r') as f:
        config = json.load(f)
    language = config.get('language', 'English')
    
    # Determine filename (HTML now) - Use consistent name per session, not timestamp
    if session:
        # One HTML file per session - overwrites when regenerated
        filename = f"session_{session['session_id']}.html"
    else:
        # Free chat still uses timestamp since no session ID
        filename = f"free_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    
    # Create PDFs directory if it doesn't exist
    pdf_dir = "assets/pdfs"
    os.makedirs(pdf_dir, exist_ok=True)
    html_path = os.path.join(pdf_dir, filename)
    
    # Generate HTML
    html_content = create_html_summary(pdf_data, session, language)
    
    # Save HTML file (overwrites existing if present)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_path


def generate_session_pdf(session_id, messages, language):
    """
    Generate HTML summary for a session (can be printed as PDF)
    
    Args:
        session_id: Session ID
        messages: List of messages in session
        language: Target language
    
    Returns:
        str: Path to generated HTML file
    """
    session = storage.get_session(session_id)
    pdf_data = generate_pdf_json(messages, language, session)
    html_path = create_html_from_json(pdf_data, session)
    
    # Update session with pdf_path
    storage.update_session(session_id, {"pdf_path": html_path})
    
    return html_path


def generate_free_chat_pdf(messages, language):
    """
    Generate HTML summary for free chat (can be printed as PDF)
    
    Args:
        messages: List of messages
        language: Target language
    
    Returns:
        str: Path to generated HTML file
    """
    pdf_data = generate_pdf_json(messages, language, session=None)
    html_path = create_html_from_json(pdf_data, is_free_chat=True)
    return html_path

