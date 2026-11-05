from dotenv import load_dotenv
from google.adk.agents import Agent

from app.settings import chat_model, sync_provider_keys

from .tools.docs import get_policy_text, search_docs

load_dotenv()
sync_provider_keys()
_MODEL = chat_model()

summarize_folder_agent = Agent(
    name="summarize_folder_agent",
    model=_MODEL,
    description="Summarizes indexed documents from their full text.",
    instruction=(
        "You only summarize. Always call get_policy_text first. "
        "The library is whatever was uploaded or ingested (PDF, TXT, or Markdown). "
        "If the user names a document or policy (PTO, security, onboarding, "
        "incidents, engineering, or a filename), pass that as filename. "
        "If they want the whole library, pass an empty filename. "
        "Folder can stay acme-handbook. "
        "Write a short bullet summary from the tool text only. Cite file "
        "paths. If the tool errors or returns nothing, say you don't know. "
        "Never invent policy. Do not answer one-off fact questions."
    ),
    tools=[get_policy_text],
)

qa_agent = Agent(
    name="qa_agent",
    model=_MODEL,
    description="Answers document questions with citations.",
    instruction=(
        "Always call search_docs first. "
        "Answer only from hits. If hits are weak or empty, say you don't know. "
        "Cite file paths. Never invent policy."
    ),
    tools=[search_docs],
)

# For adk web debugging + POST /v1/ask
root_agent = Agent(
    name="coordinator",
    model=_MODEL,
    description="Routes summaries vs handbook questions.",
    instruction=(
        "You are a router. Never answer the user yourself. Never ask "
        "permission to transfer. Never give security or policy advice.\n"
        "Transfer immediately:\n"
        "- summarize_folder_agent: summarize, overview, tl;dr, recap, "
        "explain this policy, whole folder summary.\n"
        "- qa_agent: specific questions — how many PTO days, phishing, "
        "onboarding steps, incidents, engineering, or any workplace fact.\n"
        "If unsure, transfer to qa_agent."
    ),
    sub_agents=[summarize_folder_agent, qa_agent],
)
