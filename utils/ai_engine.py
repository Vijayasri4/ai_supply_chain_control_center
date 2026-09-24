"""
AI engine for the AI Supply Chain Control Center.

Thin wrapper around the Groq API (OpenAI-compatible chat completions,
served on Groq's LPU hardware for very fast inference). All functions
take an api_key explicitly (rather than reading it globally) so the
Streamlit layer controls where the key comes from (sidebar input,
env var, etc.).
"""

from __future__ import annotations

from groq import Groq

SYSTEM_PROMPT = (
    "You are a supply chain analyst embedded in an internal dashboard. "
    "You are given structured summaries of a company's inventory, "
    "shipping, and vendor contract data. Answer the user's question "
    "using only that data. If the data doesn't contain the answer, say "
    "so plainly instead of guessing. Be concise and use bullet points "
    "or short tables where that helps. Flag concrete risks (stockouts, "
    "delayed shipments, unfavorable contract terms) when relevant."
)

CONTRACT_SUMMARY_PROMPT = (
    "You are a supply chain analyst. Summarize the following vendor "
    "contract for a busy operations manager. Cover, if present: "
    "parties involved, contract term/duration, pricing terms, payment "
    "terms, delivery/SLA obligations, penalties for late delivery, "
    "termination clauses, and anything unusual or risky. Use short "
    "headed bullet points. If a section isn't present in the text, "
    "omit it rather than guessing."
)


class AIEngineError(Exception):
    """Raised when the AI engine can't complete a request."""


def _client(api_key: str) -> Groq:
    if not api_key:
        raise AIEngineError(
            "No Groq API key configured. Add one in the sidebar or set "
            "the GROQ_API_KEY environment variable. Get a free key at "
            "https://console.groq.com/keys"
        )
    return Groq(api_key=api_key)


def ask_question(
    question: str,
    context: str,
    api_key: str,
    model: str = "openai/gpt-oss-120b",
) -> str:
    """Ask a question about the loaded supply chain data.

    Args:
        question: the user's natural-language question.
        context: text summary of inventory/shipping/contract data
            (see utils.analyzer.build_data_summary).
        api_key: Groq API key.
        model: Groq model id to use.

    Returns:
        The model's text answer.
    """
    if not question or not question.strip():
        raise AIEngineError("Please enter a question first.")

    client = _client(api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"DATA CONTEXT:\n{context}\n\n"
                        f"QUESTION: {question}"
                    ),
                },
            ],
        )
    except Exception as exc:
        raise AIEngineError(f"Groq API error: {exc}") from exc

    return response.choices[0].message.content








DISRUPTION_ADVISOR_PROMPT = (
    "You are a supply chain risk advisor. A supplier has been disrupted "
    "(disaster, strike, closure, etc.) and can no longer deliver an item "
    "on time. You are given the current stock, how fast it's being used, "
    "how many days of runway remain, and a list of alternative suppliers "
    "with their lead time and price. Give a short, decisive recommendation:\n"
    "1) State clearly whether there is enough time to act calmly or if "
    "this is urgent.\n"
    "2) Recommend the single best alternative supplier and explain why in "
    "one sentence (balance speed, cost, and reliability if given).\n"
    "3) If no alternatives were found, say so plainly and suggest concrete "
    "next steps (e.g. expedited shipping, partial substitute, safety stock).\n"
    "Keep it under 150 words. Write for a busy operations manager, not a "
    "technical audience."
)


def recommend_disruption_response(
    context: str,
    api_key: str,
    model: str = "openai/gpt-oss-120b",
) -> str:
    """Given a disruption scenario summary, get a decisive AI
    recommendation on how to respond.
    """
    client = _client(api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            max_tokens=500,
            messages=[
                {"role": "system", "content": DISRUPTION_ADVISOR_PROMPT},
                {"role": "user", "content": context},
            ],
        )
    except Exception as exc:
        raise AIEngineError(f"Groq API error: {exc}") from exc

    return response.choices[0].message.content












def summarize_contract(
    contract_text: str,
    api_key: str,
    model: str = "openai/gpt-oss-120b",
) -> str:
    """Summarize a vendor contract's key terms and risks.

    Args:
        contract_text: full extracted contract text.
        api_key: Groq API key.
        model: Groq model id to use.

    Returns:
        The model's text summary.
    """
    client = _client(api_key)

    # Keep the prompt bounded even for very long contracts.
    truncated = contract_text[:15000]

    try:
        response = client.chat.completions.create(
            model=model,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": CONTRACT_SUMMARY_PROMPT},
                {"role": "user", "content": truncated},
            ],
        )
    except Exception as exc:
        raise AIEngineError(f"Groq API error: {exc}") from exc

    return response.choices[0].message.content