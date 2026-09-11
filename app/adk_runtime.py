import uuid

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.agent import root_agent

APP_NAME = "acme-docs-copilot"
USER_ID = "api"


def build_runner() -> Runner:
    return Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=InMemorySessionService(),
    )


def _unwrap_tool_payload(response) -> dict:
    if not isinstance(response, dict):
        return {}
    if "hits" in response or "status" in response:
        return response
    inner = response.get("result")
    return inner if isinstance(inner, dict) else response


def _citations_from_search(payload: dict) -> list[dict]:
    return [
        {"path": hit["path"], "score": float(hit["score"])}
        for hit in payload.get("hits", [])
        if isinstance(hit, dict) and "path" in hit
    ]


def _citations_from_policy(payload: dict) -> list[dict]:
    return [
        {"path": item["path"], "score": 1.0}
        for item in payload.get("files", [])
        if isinstance(item, dict) and item.get("path")
    ]


async def run_ask(runner: Runner, question: str) -> dict:
    session_id = str(uuid.uuid4())
    await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text=question)],
    )

    answer = ""
    citations: list[dict] = []
    trace: list[str] = []

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=message,
    ):
        author = event.author or ""
        if author and author != "user" and (not trace or trace[-1] != author):
            trace.append(author)

        for fr in event.get_function_responses():
            payload = _unwrap_tool_payload(fr.response)
            if fr.name == "search_docs":
                citations = _citations_from_search(payload)
            elif fr.name == "get_policy_text":
                citations = _citations_from_policy(payload)

        if event.is_final_response() and event.content and event.content.parts:
            texts = [p.text for p in event.content.parts if p.text]
            if texts:
                answer = texts[0]

    return {
        "answer": answer,
        "citations": citations,
        "agent_trace": trace,
    }