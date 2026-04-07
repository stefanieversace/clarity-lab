import os
import streamlit as st
import anthropic

st.set_page_config(page_title="Explain It Like I'm Smart (But Lazy)", layout="centered")

api_key = os.getenv("ANTHROPIC_API_KEY")

st.title("🧠 Clarity Lab")
st.caption("Understand anything quickly — clear, structured, no fluff.")

topic = st.text_input("What do you want to understand?")

if st.button("Explain"):
    if not api_key:
        st.error("Missing ANTHROPIC_API_KEY environment variable.")
    elif not topic.strip():
        st.warning("Please enter a topic.")
    else:
        client = anthropic.Anthropic(api_key=api_key)

        prompt = f"""
You are an expert communicator.

Explain the topic: "{topic}"

Provide 3 sections:

1. 30-Second Take
2. 2-Minute Understanding
3. Deeper Insight

Rules:
- Do not sound condescending
- Do not oversimplify
- Be sharp, modern, and clear
- Use bullet points where helpful
"""

        with st.spinner("Thinking..."):
            response = client.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=900,
                messages=[{"role": "user", "content": prompt}],
            )

        result = response.content[0].text
        st.markdown(result)
