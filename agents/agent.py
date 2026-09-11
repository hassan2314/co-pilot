from google.adk.agents import Agent
from .tools.docs import ingest_folder, clear_index, search_docs

ingest_agent = Agent(
    name="ingest_agent",
    model="gemini-3.1-flash-lite",  # same family you already use
    description="Ingests a markdown folder into the docs index.",
    instruction=(
        "You only ingest. Call ingest_folder with the given folder. "
        "Optionally clear_index first if the user asked to reindex. "
        "Return the tool result. Do not answer product questions."
    ),
    tools=[ingest_folder, clear_index],
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

# For adk web debugging
root_agent = Agent(
    name="coordinator",
    model="gemini-3.1-flash-lite",
    description="Routes ingest vs questions.",
    instruction=(
        "You are a router. Never answer the user yourself. Never ask "
        "permission to transfer. Never give security or policy advice.\n"
        "Transfer immediately:\n"
        "- ingest_agent: user wants to ingest, index, reindex, load docs, "
        "or clear the index. Folder names are relative to sample_docs/ "
        "(example: acme-handbook).\n"
        "- qa_agent: everything else — handbook, PTO, security, phishing, "
        "email links, incidents, onboarding, engineering, or any workplace "
        "question.\n"
        "If unsure, transfer to qa_agent."
    ),
    sub_agents=[ingest_agent, qa_agent],
)