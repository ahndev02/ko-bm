"""Official KoBALT-700 prompt template constants and message builder.

Official protocol (upstream-verified):
  system: "당신은 문제를 해결하는 전문가입니다."
  user template (verbatim structure with {question} substituted):
    "다음 문제에 대해서 충분히 생각하고 추론하여, 10개의 보기(A, B, C, D, E, F, G, H, I, J) 중 정답을 고르세요.\\n\\n{question}\\n\\n답변은 반드시 다음 형식을 엄격히 지켜야 합니다: \\"정답은 [정답 보기]입니다.\\"로 끝나야하고, [정답 보기]는 A, B, C, D, E, F, G, H, I, J 중 하나여야 합니다.정답: 문제를 풀기 위해, 한 번 천천히 생각해봅시다."
"""

from __future__ import annotations

import hashlib

SYSTEM_PROMPT: str = "당신은 문제를 해결하는 전문가입니다."

USER_TEMPLATE: str = (
    "다음 문제에 대해서 충분히 생각하고 추론하여, "
    "10개의 보기(A, B, C, D, E, F, G, H, I, J) 중 정답을 고르세요."
    "\n\n{question}\n\n"
    '답변은 반드시 다음 형식을 엄격히 지켜야 합니다: "정답은 [정답 보기]입니다."로 끝나야하고, '
    "[정답 보기]는 A, B, C, D, E, F, G, H, I, J 중 하나여야 합니다."
    "정답: 문제를 풀기 위해, 한 번 천천히 생각해봅시다."
)

# Aliases for convenience / backwards-compat with the spec wording.
OFFICIAL_SYSTEM_PROMPT: str = SYSTEM_PROMPT
OFFICIAL_USER_TEMPLATE: str = USER_TEMPLATE


def build_messages(
    question: str,
    system: str = SYSTEM_PROMPT,
    user_template: str = USER_TEMPLATE,
) -> list[dict]:
    """Build the system+user chat messages list for one item.

    Args:
        question: The item's Question text (options A-J embedded).
        system: System message text (defaults to the official text).
        user_template: Template containing ``{question}`` (defaults to official).

    Returns:
        ``[{"role": "system", ...}, {"role": "user", ...}]``.
    """
    user_content = user_template.replace("{question}", question)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]


def build_messages_from_config(question: str, config) -> list[dict]:
    """Build messages using a RunConfig's prompt section."""
    prompt = config.prompt
    return build_messages(question, system=prompt.system, user_template=prompt.user_template)


def prompt_template_hash(system: str = SYSTEM_PROMPT, user_template: str = USER_TEMPLATE) -> str:
    """Stable sha256 hash of the prompt template (system + user template)."""
    h = hashlib.sha256()
    h.update(system.encode("utf-8"))
    h.update(b"\x00")
    h.update(user_template.encode("utf-8"))
    return h.hexdigest()
