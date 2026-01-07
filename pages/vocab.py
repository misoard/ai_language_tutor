import streamlit as st
from utils import storage
from sidebar import render_sidebar
import pandas as pd
import openai
import json

st.set_page_config(page_title="Vocabulary", page_icon="📚", layout="wide")
render_sidebar()

# --- Load Configuration from config.json ---
with open('utils/config.json', 'r') as config_file:
    config = json.load(config_file)

# Extract parameters from config
OPENAI_MODEL = config.get('openai_model_name', 'gpt-4o')
TEMPERATURE = config.get('temperature', 0.7)
LANGUAGE = config.get('language', 'English')

# --- Load Vocabulary ---
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

# --- Page Content ---
st.title("📚 Vocabulary")
st.write("Review the words that you have learned so far. You can remove or add new words in the side panel.")

# Sidebar to display word list
st.sidebar.header("🗉 Vocabulary List")

# Display vocabulary in sidebar with delete buttons
if vocab_list:
    for i, word_entry in enumerate(vocab_list):
        col1, col2 = st.sidebar.columns([0.7, 0.3])  # Adjust for better alignment
        col1.markdown(f"**{word_entry['word']}**")  # Display word
        if col2.button("❌", key=f"delete_{i}"):  # Inline delete button
            vocab_list.pop(i)
            storage.save_vocabulary(vocab_list)
            st.rerun()  # Refresh UI after deletion
else:
    st.sidebar.write("No words in your vocabulary.")

# --- Vocabulary Table Display ---
if vocab_list:
    # Convert to DataFrame for display
    vocab_df = pd.DataFrame(vocab_list)

    # Rename columns for clarity
    vocab_df = vocab_df.rename(columns={
        "word": "Word",
        "translation": "Translation",
        "example": "Example"
    })

    # Display table using st.table for proper text wrapping
    st.table(vocab_df)
else:
    st.warning("Your vocabulary list is empty. Add new words using the sidebar.")

# --- Add New Word Section ---
new_word = st.sidebar.text_input("New word", key="new_vocab_word")

if st.sidebar.button("Add Word"):
    if new_word.strip() and all(w["word"] != new_word.strip() for w in vocab_list):
        # Generate explanation and example using OpenAI
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
            try:
                response = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[{"role": "system", "content": "You provide translation and examples in {LANGUAGE}."},
                              {"role": "user", "content": prompt}],
                    temperature=TEMPERATURE
                )

                # Parse the response
                content = response.choices[0].message.content.strip()
                translation, example = "", ""

                for line in content.splitlines():
                    if line.startswith("Translation:"):
                        translation = line.replace("Translation:", "").strip()
                    elif line.startswith("Example:"):
                        example = line.replace("Example:", "").strip()

                if translation and example:
                    new_entry = {
                        "word": new_word.strip(),
                        "translation": translation,
                        "example": example
                    }
                    
                    # Save immediately after generation
                    vocab_list.append(new_entry)
                    storage.save_vocabulary(vocab_list)
                    
                    st.success(f"Added '{new_word}' with translation and example.")
                    st.rerun()
                else:
                    st.error("Failed to parse translation and example. Please try again.")

            except Exception as e:
                st.error(f"Error fetching data from OpenAI API: {e}")
    else:
        st.warning("Please enter a unique word.")
