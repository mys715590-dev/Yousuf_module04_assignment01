"""Streamlit UI for SmartQuote AI. Run: streamlit run app.py"""

import os
import json

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from agent import run_agent
from storage import save_approved_quote, SAVED_QUOTES
from tools import get_service_catalog


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

load_dotenv()

st.set_page_config(
    page_title="SmartQuote AI | Aicademy 360",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 SmartQuote AI")
st.caption("My Project | Smart Business Quotation Assistant")

st.info(
    "CLASSROOM DEMO: PKR prices are fictional. "
    "Tax is excluded. Nothing is automatically sent to customers."
)


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "chat" not in st.session_state:
    st.session_state.chat = []

if "draft" not in st.session_state:
    st.session_state.draft = None

if "latest_tool_log" not in st.session_state:
    st.session_state.latest_tool_log = []

if "saved_draft" not in st.session_state:
    st.session_state.saved_draft = False


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:

    st.header("🧰 Agent Tools")

    st.write("1. `get_service_catalog`")
    st.write("2. `get_business_policy`")
    st.write("3. `calculate_quote`")

    st.divider()

    st.subheader("⚙️ AI Configuration")

    st.write("**Groq Model**")

    st.code(
        os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        language="text"
    )

    st.divider()

    if st.button(
        "🧹 Clear Conversation",
        use_container_width=True
    ):

        st.session_state.chat = []
        st.session_state.draft = None
        st.session_state.latest_tool_log = []
        st.session_state.saved_draft = False

        st.rerun()

    with st.expander("📦 Sample Service Catalog"):

        try:
            catalog = get_service_catalog()

            if catalog.get("services"):
                st.dataframe(
                    pd.DataFrame(catalog["services"]),
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.warning("No services available.")

        except Exception:
            st.error("Unable to load service catalog.")


# --------------------------------------------------
# MAIN LAYOUT
# --------------------------------------------------

left, right = st.columns(
    [1.65, 1],
    gap="large"
)


# --------------------------------------------------
# CHAT INTERFACE
# --------------------------------------------------

with left:

    st.subheader("💬 Talk to Your Agent")

    # Display previous conversation.
    for entry in st.session_state.chat:

        with st.chat_message(entry["role"]):
            st.markdown(entry["content"])

    prompt = st.chat_input(
        "Example: Quote 12 social media posts and 4 reels"
    )

    if prompt:

        old_history = list(st.session_state.chat)

        # Reset previous quotation draft.
        st.session_state.draft = None
        st.session_state.saved_draft = False
        st.session_state.latest_tool_log = []

        st.session_state.chat.append({
            "role": "user",
            "content": prompt
        })

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):

            if not os.getenv("GROQ_API_KEY"):

                answer = (
                    "GROQ_API_KEY is missing. "
                    "Please add your API key to the .env file "
                    "and restart Streamlit."
                )

                st.error(answer)

                st.session_state.chat.append({
                    "role": "assistant",
                    "content": answer
                })

            else:

                with st.spinner(
                    "🤖 SmartQuote AI is processing your request..."
                ):

                    try:

                        result = run_agent(
                            prompt,
                            history=old_history
                        )

                        answer = result.get(
                            "answer",
                            "No response was generated."
                        )

                        st.markdown(answer)

                        st.session_state.chat.append({
                            "role": "assistant",
                            "content": answer
                        })

                        st.session_state.latest_tool_log = (
                            result.get("tool_log", [])
                        )

                        new_quote = result.get("quote")

                        if (
                            isinstance(new_quote, dict)
                            and new_quote.get("status")
                            == "DRAFT_AWAITING_HUMAN_APPROVAL"
                        ):

                            st.session_state.draft = new_quote

                    except Exception as exc:

                        error_message = (
                            "The AI request failed. "
                            "Please check your API key, model, "
                            "internet connection and account limits."
                        )

                        st.error(error_message)

                        with st.expander(
                            "Technical Error (For Instructor)"
                        ):
                            st.code(type(exc).__name__)

        st.rerun()


# --------------------------------------------------
# AGENT ACTIVITY PANEL
# --------------------------------------------------

with right:

    st.subheader("🔍 Agent Activity")

    if st.session_state.latest_tool_log:

        for number, step in enumerate(
            st.session_state.latest_tool_log,
            start=1
        ):

            with st.expander(
                f"Step {number}: {step['tool']}",
                expanded=number == 1
            ):

                st.write("**Arguments Chosen by AI**")

                st.code(
                    step["arguments"],
                    language="json"
                )

                st.write("**Result Computed by Python**")

                st.json(step["result"])

    else:

        st.caption(
            "Ask the agent a question to see its Python tool calls here."
        )

    # --------------------------------------------------
    # QUOTATION PANEL
    # --------------------------------------------------

    st.divider()

    st.subheader("📄 Latest Draft Quotation")

    quote = st.session_state.draft

    if quote:

        items = quote.get("items", [])

        if items:

            st.dataframe(
                pd.DataFrame(items)[
                    [
                        "service",
                        "quantity",
                        "unit_price",
                        "line_total"
                    ]
                ],
                hide_index=True,
                use_container_width=True
            )

        st.metric(
            "Subtotal",
            f"{quote['currency']} {quote['subtotal']}"
        )

        if quote["discount_amount"] != "0.00":

            st.caption(
                f"Discount: {quote['discount_pct']}% | "
                f"Saved: {quote['currency']} "
                f"{quote['discount_amount']}"
            )

        st.metric(
            "Total (Tax Excluded)",
            f"{quote['currency']} {quote['total']}"
        )

        st.caption(quote.get("tax_note", "Tax excluded."))

        st.warning(
            "This is a draft quotation. Human approval is required."
        )

        client_name = st.text_input(
            "Client Name for Approved Record",
            key="client_name"
        )

        if st.button(
            "✅ Save Approved Quote",
            disabled=st.session_state.saved_draft,
            use_container_width=True
        ):

            try:

                saved = save_approved_quote(
                    quote,
                    client_name
                )

            except ValueError as exc:

                st.error(str(exc))

            else:

                st.session_state.saved_draft = True

                st.success(
                    f"Quotation successfully saved! "
                    f"Reference: {saved['quote_id']}"
                )

        if st.session_state.saved_draft:

            st.caption(
                "This quotation has already been saved. "
                "Generate a new quotation to save another."
            )

        # Download draft quotation.
        st.download_button(
            "⬇ Download Draft JSON",
            data=json.dumps(
                quote,
                indent=2,
                ensure_ascii=False
            ),
            file_name="draft_quote.json",
            mime="application/json",
            use_container_width=True
        )

    else:

        st.caption(
            "Your quotation will appear here after "
            "calculate_quote is successfully executed."
        )

    # --------------------------------------------------
    # APPROVED QUOTATIONS
    # --------------------------------------------------

    if SAVED_QUOTES.exists():

        st.divider()

        st.subheader("📁 Approved Quotations")

        st.download_button(
            "⬇ Download Approved Quotes CSV",
            data=SAVED_QUOTES.read_bytes(),
            file_name="approved_quotes.csv",
            mime="text/csv",
            use_container_width=True
        )