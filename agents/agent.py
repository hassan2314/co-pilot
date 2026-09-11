from google.adk.agents import Agent
from .tools.docs import get_policy_text, search_docs

summarize_folder_agent = Agent(
    name="summarize_folder_agent",
    model="gemini-3.1-flash-lite",
    description="Summarizes a handbook policy or folder from source markdown.",
    instruction=(
        "You only summarize. Always call get_policy_text first. "
        "Use folder acme-handbook unless the user named another folder. "
        "If they name a policy (PTO, security, onboarding, incidents, "
        "eng practices), pass that as filename. If they want the whole "
        "handbook, pass an empty filename. "
        "Write a short bullet summary from the tool text only. Cite file "
        "paths. If the tool errors or returns nothing, say you don't know. "
        "Never invent policy. Do not answer one-off fact questions."
    ),
    tools=[get_policy_text],
)

qa_agent = Agent(
    name="qa_agent",
    model="gemini-3.1-flash-lite",
    description="Answers company-doc questions with citations.",
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
    model="gemini-3.1-flash-lite",
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
