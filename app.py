import os
import re
import html
from datetime import datetime
from typing import List, Dict, Any

import streamlit as st
from anthropic import Anthropic

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Clarity Lab",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# APP-WIDE CONSTANTS
# =========================================================
APP_NAME = "Clarity Lab"
APP_TAGLINE = "Understand anything quickly — clear, structured, no fluff."
DEFAULT_MODEL = "claude-sonnet-4-6"

TONE_OPTIONS = {
    "Balanced": "Clear, modern, sharp, and neutral. Intelligent but accessible.",
    "Professional": "Polished, concise, executive-ready, and professional.",
    "Analyst": "Structured, precise, evidence-oriented, and insight-driven.",
    "Friendly": "Warm, encouraging, simple, and easy to follow.",
    "Brutally Clear": "Direct, efficient, no waffle, no filler, just clarity.",
}

DEPTH_OPTIONS = {
    "Fast": {
        "max_tokens": 900,
        "description": "Quick, useful, and concise.",
    },
    "Standard": {
        "max_tokens": 1400,
        "description": "Balanced detail for most topics.",
    },
    "Deep Dive": {
        "max_tokens": 2200,
        "description": "More layered, more nuance, more examples.",
    },
}

EXAMPLE_TOPICS = [
    "What is inflation?",
    "How does Docker work?",
    "What is zero trust security?",
    "Explain attachment theory",
    "How do AI agents differ from chatbots?",
    "What is a hedge fund?",
    "What is the CIA triad?",
    "Explain venture capital like I’m smart but lazy",
]

# =========================================================
# CUSTOM CSS
# =========================================================
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }

        .app-hero {
            padding: 1.4rem 1.4rem 1.1rem 1.4rem;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 20px;
            background:
                radial-gradient(circle at top right, rgba(120, 119, 198, 0.18), transparent 30%),
                linear-gradient(135deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
            margin-bottom: 1rem;
        }

        .hero-title {
            font-size: 2rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 0.2rem;
        }

        .hero-subtitle {
            font-size: 1rem;
            opacity: 0.85;
            margin-bottom: 0.8rem;
        }

        .metric-pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.35rem;
        }

        .metric-pill {
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 999px;
            padding: 0.45rem 0.8rem;
            font-size: 0.87rem;
            background: rgba(255,255,255,0.03);
        }

        .section-card {
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 18px;
            padding: 1rem 1rem 0.7rem 1rem;
            background: rgba(255,255,255,0.02);
            margin-bottom: 0.9rem;
        }

        .section-label {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            opacity: 0.65;
            margin-bottom: 0.35rem;
            font-weight: 700;
        }

        .tiny-muted {
            font-size: 0.85rem;
            opacity: 0.72;
        }

        .history-card {
            border-left: 3px solid rgba(255,255,255,0.12);
            padding-left: 0.8rem;
            margin-bottom: 1rem;
        }

        .stButton>button, .stDownloadButton>button {
            border-radius: 12px !important;
            font-weight: 600 !important;
        }

        .footer-note {
            opacity: 0.7;
            font-size: 0.84rem;
            margin-top: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# SESSION STATE
# Streamlit session state is the right way to persist values
# across reruns in a user session. :contentReference[oaicite:1]{index=1}
# =========================================================
if "history" not in st.session_state:
    st.session_state.history = []

if "last_response_markdown" not in st.session_state:
    st.session_state.last_response_markdown = ""

if "last_topic" not in st.session_state:
    st.session_state.last_topic = ""

if "last_prompt_payload" not in st.session_state:
    st.session_state.last_prompt_payload = []

if "last_generated_at" not in st.session_state:
    st.session_state.last_generated_at = None

if "saved_count" not in st.session_state:
    st.session_state.saved_count = 0

# =========================================================
# CLIENT
# Anthropic's official SDK supports Anthropic() and reads
# ANTHROPIC_API_KEY from the environment. :contentReference[oaicite:2]{index=2}
# =========================================================
def get_client() -> Anthropic | None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return Anthropic(api_key=api_key)

# =========================================================
# HELPERS
# =========================================================
def sanitize_topic(topic: str) -> str:
    """Clean up whitespace without changing meaning."""
    return re.sub(r"\s+", " ", topic.strip())

def estimate_read_time(text: str) -> int:
    words = len(re.findall(r"\w+", text))
    # Rough reading speed ~200 wpm
    return max(1, round(words / 200))

def markdown_to_html_document(title: str, markdown_text: str) -> str:
    """
    Creates a simple downloadable HTML file.
    This is intentionally lightweight and safe.
    """
    escaped_title = html.escape(title)
    escaped_body = html.escape(markdown_text)

    # Minimal formatting for readability
    body_html = escaped_body.replace("\n\n", "</p><p>").replace("\n", "<br>")
    body_html = f"<p>{body_html}</p>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{escaped_title}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      max-width: 860px;
      margin: 48px auto;
      padding: 0 20px;
      color: #1a1a1a;
      line-height: 1.65;
    }}
    h1 {{
      font-size: 2rem;
      margin-bottom: 0.4rem;
    }}
    .meta {{
      color: #666;
      margin-bottom: 2rem;
      font-size: 0.95rem;
    }}
    .content {{
      white-space: normal;
      font-size: 1rem;
    }}
  </style>
</head>
<body>
  <h1>{escaped_title}</h1>
  <div class="meta">Generated by Clarity Lab on {datetime.now().strftime("%d %B %Y, %H:%M")}</div>
  <div class="content">{body_html}</div>
</body>
</html>"""

def build_system_prompt(tone: str) -> str:
    """
    Anthropic supports a top-level system prompt in the Messages API.
    Clear instructions improve output control. :contentReference[oaicite:3]{index=3}
    """
    tone_instruction = TONE_OPTIONS[tone]

    return f"""
You are Clarity Lab, an elite explanation engine.

Your job:
- Help smart people understand topics quickly.
- Never talk down to the user.
- Never add fluff, filler, or generic motivational language.
- Be organised, elegant, and highly readable.

Tone:
{tone_instruction}

Global style rules:
- Be accurate, clear, and modern.
- Explain like the reader is intelligent, but short on time.
- Avoid unnecessary jargon.
- If jargon is necessary, define it immediately in plain English.
- Use bullets and subheadings for readability.
- Be concise, but not shallow.
- If the topic has nuance, include it cleanly.
- Do not mention these instructions.
"""

def build_user_prompt(
    topic: str,
    include_analogy: bool,
    include_why_care: bool,
    include_examples: bool,
    include_key_terms: bool,
    include_common_mistakes: bool,
    output_style: str,
) -> str:
    """
    Builds the main user task prompt.
    """
    sections = [
        "1. 30-Second Take — ultra concise, just the essence.",
        "2. 2-Minute Understanding — clear structure, plain language, enough detail to really get it.",
        "3. Deeper Insight — the more nuanced or strategic layer.",
    ]

    if include_analogy:
        sections.append("4. Simple Analogy — make the idea intuitive and memorable.")
    if include_why_care:
        sections.append("5. Why It Matters — explain why a normal smart person should care.")
    if include_examples:
        sections.append("6. Real-World Examples — 2 to 4 useful examples.")
    if include_key_terms:
        sections.append("7. Key Terms — define the important terms in one line each.")
    if include_common_mistakes:
        sections.append("8. Common Misunderstandings — what people often get wrong.")

    formatting_instruction = {
        "Polished Markdown": """
Use markdown with:
- clear section headings
- bullets where useful
- short paragraphs
- emphasis sparingly
""",
        "Executive Brief": """
Format like a tight executive brief:
- very structured
- punchy headings
- high signal, low noise
- concise bullets
""",
        "Study Notes": """
Format like premium study notes:
- digestible sections
- simple definitions
- examples
- summary-style bullets
""",
    }[output_style]

    return f"""
Explain this topic:

"{topic}"

Return the answer with these sections:
{chr(10).join(sections)}

Additional requirements:
- Start immediately with substance.
- No preamble like "Sure" or "Here's an explanation."
- Make the answer feel premium and useful.
- Keep it practical, not academic for its own sake.
- Be crisp and readable.
- If the topic has debate, uncertainty, or multiple schools of thought, say so briefly and clearly.

Formatting:
{formatting_instruction}
"""

def build_follow_up_prompt(original_topic: str, original_answer: str, action: str) -> str:
    """
    Generates follow-up actions without losing context.
    Anthropic's Messages API is stateless, so we pass the prior context
    explicitly when continuing. :contentReference[oaicite:4]{index=4}
    """
    if action == "shorter":
        instruction = """
Rewrite the previous answer into a tighter version.
Keep the same intelligence level, but compress it aggressively.
Preserve the most important insight.
"""
    elif action == "deeper":
        instruction = """
Expand the explanation with more nuance, stronger examples,
and a more strategic understanding of the topic.
Do not repeat the same points word-for-word.
"""
    elif action == "simpler":
        instruction = """
Rewrite the answer in simpler language without making it childish.
Keep it smart, but easier to process quickly.
"""
    elif action == "examples":
        instruction = """
Keep the explanation concise but add better real-world examples.
Make the examples modern, concrete, and memorable.
"""
    else:
        instruction = """
Improve the answer while keeping it clear and readable.
"""

    return f"""
Original topic:
{original_topic}

Previous answer:
{original_answer}

Task:
{instruction}
"""

def call_claude(
    system_prompt: str,
    messages: List[Dict[str, Any]],
    model: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """
    Calls Anthropic Messages API via official SDK.
    """
    client = get_client()
    if client is None:
        raise RuntimeError("Missing ANTHROPIC_API_KEY environment variable.")

    response = client.messages.create(
        model=model,
        system=system_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=messages,
    )

    # Extract text blocks robustly
    text_parts = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)

    return "\n".join(text_parts).strip()

def save_to_history(topic: str, answer: str, tone: str, depth: str) -> None:
    st.session_state.history.insert(
        0,
        {
            "topic": topic,
            "answer": answer,
            "tone": tone,
            "depth": depth,
            "timestamp": datetime.now().strftime("%d %b %Y • %H:%M"),
        },
    )

def render_history() -> None:
    if not st.session_state.history:
        st.caption("No saved explanations yet.")
        return

    for idx, item in enumerate(st.session_state.history[:12], start=1):
        with st.container():
            st.markdown("<div class='history-card'>", unsafe_allow_html=True)
            st.markdown(f"**{idx}. {item['topic']}**")
            st.caption(f"{item['timestamp']} · Tone: {item['tone']} · Depth: {item['depth']}")
            preview = item["answer"][:240].replace("\n", " ")
            if len(item["answer"]) > 240:
                preview += "..."
            st.write(preview)
            st.markdown("</div>", unsafe_allow_html=True)

def render_hero():
    st.markdown(
        f"""
        <div class="app-hero">
            <div class="hero-title">🧠 {APP_NAME}</div>
            <div class="hero-subtitle">{APP_TAGLINE}</div>
            <div class="metric-pill-row">
                <div class="metric-pill">30-second take</div>
                <div class="metric-pill">2-minute understanding</div>
                <div class="metric-pill">deeper insight</div>
                <div class="metric-pill">analogy mode</div>
                <div class="metric-pill">downloadable output</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.title("Control Panel")
    st.caption("Tune the explanation so it feels like a real product, not a generic chatbot.")

    tone = st.selectbox(
        "Tone",
        list(TONE_OPTIONS.keys()),
        index=0,
        help="Choose the voice of the explanation.",
    )

    depth = st.selectbox(
        "Depth",
        list(DEPTH_OPTIONS.keys()),
        index=1,
        help="Controls detail and response length.",
    )

    output_style = st.selectbox(
        "Output format",
        ["Polished Markdown", "Executive Brief", "Study Notes"],
        index=0,
    )

    temperature = st.slider(
        "Creativity",
        min_value=0.0,
        max_value=1.0,
        value=0.3,
        step=0.1,
        help="Lower = tighter and more deterministic. Higher = more stylistic variation.",
    )

    st.markdown("---")
    st.subheader("Extra sections")

    include_analogy = st.checkbox("Include analogy", value=True)
    include_why_care = st.checkbox("Include why it matters", value=True)
    include_examples = st.checkbox("Include real-world examples", value=True)
    include_key_terms = st.checkbox("Include key terms", value=False)
    include_common_mistakes = st.checkbox("Include common misunderstandings", value=False)

    st.markdown("---")
    st.subheader("Model settings")
    model_name = st.text_input(
        "Model",
        value=DEFAULT_MODEL,
        help="You can replace this with a different Anthropic model available to your account.",
    )
    st.caption("The official Anthropic docs show the Python SDK using `Anthropic()` with `messages.create(...)`. :contentReference[oaicite:5]{index=5}")

    st.markdown("---")
    st.subheader("Saved explanations")
    render_history()

# =========================================================
# MAIN LAYOUT
# =========================================================
render_hero()

left_col, right_col = st.columns([1.35, 1], gap="large")

with left_col:
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-label'>Ask Clarity Lab</div>", unsafe_allow_html=True)

    topic = st.text_area(
        "What do you want to understand?",
        value=st.session_state.last_topic,
        height=140,
        placeholder="Try: What is inflation and why does it matter?\nOr: Explain Docker like I’m smart but lazy.",
        label_visibility="collapsed",
    )

    example_cols = st.columns(4)
    for i, example in enumerate(EXAMPLE_TOPICS[:4]):
        if example_cols[i].button(example, use_container_width=True):
            st.session_state.last_topic = example
            st.rerun()

    example_cols_2 = st.columns(4)
    for i, example in enumerate(EXAMPLE_TOPICS[4:8]):
        if example_cols_2[i].button(example, use_container_width=True):
            st.session_state.last_topic = example
            st.rerun()

    c1, c2, c3 = st.columns([1, 1, 1.1])

    generate_clicked = c1.button("Generate Explanation", type="primary", use_container_width=True)
    clear_clicked = c2.button("Clear", use_container_width=True)
    save_clicked = c3.button("Save Current to History", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    if clear_clicked:
        st.session_state.last_response_markdown = ""
        st.session_state.last_topic = ""
        st.session_state.last_prompt_payload = []
        st.session_state.last_generated_at = None
        st.rerun()

    if save_clicked and st.session_state.last_response_markdown:
        save_to_history(
            topic=st.session_state.last_topic or "Untitled topic",
            answer=st.session_state.last_response_markdown,
            tone=tone,
            depth=depth,
        )
        st.session_state.saved_count += 1
        st.success("Saved to history.")

    if generate_clicked:
        cleaned_topic = sanitize_topic(topic)

        if not cleaned_topic:
            st.warning("Enter a topic first.")
        elif get_client() is None:
            st.error(
                "Missing `ANTHROPIC_API_KEY`. Set it in your terminal before running the app."
            )
            st.code('export ANTHROPIC_API_KEY="your_key_here"', language="bash")
        else:
            system_prompt = build_system_prompt(tone)
            user_prompt = build_user_prompt(
                topic=cleaned_topic,
                include_analogy=include_analogy,
                include_why_care=include_why_care,
                include_examples=include_examples,
                include_key_terms=include_key_terms,
                include_common_mistakes=include_common_mistakes,
                output_style=output_style,
            )

            payload = [{"role": "user", "content": user_prompt}]

            try:
                with st.spinner("Building a cleaner explanation..."):
                    answer = call_claude(
                        system_prompt=system_prompt,
                        messages=payload,
                        model=model_name,
                        max_tokens=DEPTH_OPTIONS[depth]["max_tokens"],
                        temperature=temperature,
                    )

                st.session_state.last_response_markdown = answer
                st.session_state.last_topic = cleaned_topic
                st.session_state.last_prompt_payload = payload
                st.session_state.last_generated_at = datetime.now().strftime("%d %B %Y, %H:%M")

            except Exception as e:
                st.exception(e)

with right_col:
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-label'>What makes this feel premium</div>", unsafe_allow_html=True)
    st.markdown(
        """
- Layered explanations instead of one flat response  
- Tone control so it can sound analyst-level, professional, or more human  
- Optional analogy, examples, and “why it matters”  
- Saved history so the app feels persistent  
- Follow-up actions instead of forcing users to rewrite prompts  
- Download options so outputs become portable notes
"""
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-label'>Setup</div>", unsafe_allow_html=True)
    st.code("pip install streamlit anthropic", language="bash")
    st.code('export ANTHROPIC_API_KEY="your_key_here"', language="bash")
    st.caption(
        "Anthropic’s official SDK supports `Anthropic()` and environment-based API keys, and Streamlit’s download button is meant for serving generated files directly in-app. :contentReference[oaicite:6]{index=6}"
    )
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# OUTPUT
# =========================================================
st.markdown("## Output")

if st.session_state.last_response_markdown:
    response_text = st.session_state.last_response_markdown
    read_time = estimate_read_time(response_text)

    top_a, top_b, top_c, top_d = st.columns(4)
    top_a.metric("Tone", tone)
    top_b.metric("Depth", depth)
    top_c.metric("Read time", f"{read_time} min")
    top_d.metric("Generated", st.session_state.last_generated_at or "—")

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(response_text)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### Follow-up actions")
    f1, f2, f3, f4 = st.columns(4)

    shorter = f1.button("Make it shorter", use_container_width=True)
    deeper = f2.button("Go deeper", use_container_width=True)
    simpler = f3.button("Make it simpler", use_container_width=True)
    more_examples = f4.button("Better examples", use_container_width=True)

    selected_action = None
    if shorter:
        selected_action = "shorter"
    elif deeper:
        selected_action = "deeper"
    elif simpler:
        selected_action = "simpler"
    elif more_examples:
        selected_action = "examples"

    if selected_action:
        try:
            follow_up_prompt = build_follow_up_prompt(
                original_topic=st.session_state.last_topic,
                original_answer=st.session_state.last_response_markdown,
                action=selected_action,
            )

            # Because the Messages API is stateless, we send context again. :contentReference[oaicite:7]{index=7}
            follow_up_messages = [
                {
                    "role": "user",
                    "content": follow_up_prompt,
                }
            ]

            with st.spinner("Refining the explanation..."):
                refined_answer = call_claude(
                    system_prompt=build_system_prompt(tone),
                    messages=follow_up_messages,
                    model=model_name,
                    max_tokens=DEPTH_OPTIONS[depth]["max_tokens"],
                    temperature=temperature,
                )

            st.session_state.last_response_markdown = refined_answer
            st.session_state.last_generated_at = datetime.now().strftime("%d %B %Y, %H:%M")
            st.rerun()

        except Exception as e:
            st.exception(e)

    st.markdown("### Download")
    dl1, dl2 = st.columns(2)

    markdown_filename = f"clarity-lab-{re.sub(r'[^a-zA-Z0-9]+', '-', st.session_state.last_topic.lower()).strip('-') or 'explanation'}.md"
    html_filename = markdown_filename.replace(".md", ".html")

    dl1.download_button(
        label="Download as Markdown",
        data=response_text,
        file_name=markdown_filename,
        mime="text/markdown",
        use_container_width=True,
    )

    dl2.download_button(
        label="Download as HTML",
        data=markdown_to_html_document(st.session_state.last_topic, response_text),
        file_name=html_filename,
        mime="text/html",
        use_container_width=True,
    )

    st.markdown("### Rate this answer")
    rating = st.feedback("thumbs", key="answer_feedback")
    if rating is not None:
        if rating == 1:
            st.success("Nice — save that output if you want to reuse it.")
        elif rating == 0:
            st.info("Try changing tone, depth, or follow-up actions to tighten it up.")
    st.caption(
        "Streamlit includes a built-in feedback widget designed for AI-style apps. :contentReference[oaicite:8]{index=8}"
    )

else:
    st.info("Your explanation will appear here once you generate one.")

# =========================================================
# FOOTER
# =========================================================
st.markdown(
    """
    <div class="footer-note">
        Built for people who want understanding fast, without being talked down to.
    </div>
    """,
    unsafe_allow_html=True,
)
