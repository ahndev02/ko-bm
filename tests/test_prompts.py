"""Unit tests: official Korean CoT prompt builder.

Expected strings are copied verbatim from the spec (section 9), not
from the implementation, so drift in src/ breaks these tests.
"""

from __future__ import annotations

from kobalt_eval.prompts import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    build_messages,
    prompt_template_hash,
)

EXPECTED_SYSTEM = "당신은 문제를 해결하는 전문가입니다."

EXPECTED_USER_TEMPLATE = (
    "다음 문제에 대해서 충분히 생각하고 추론하여, "
    "10개의 보기(A, B, C, D, E, F, G, H, I, J) 중 정답을 고르세요."
    "\n\n{question}\n\n"
    '답변은 반드시 다음 형식을 엄격히 지켜야 합니다: "정답은 [정답 보기]입니다."로 끝나야하고, '
    "[정답 보기]는 A, B, C, D, E, F, G, H, I, J 중 하나여야 합니다."
    "정답: 문제를 풀기 위해, 한 번 천천히 생각해봅시다."
)


def test_module_constants_match_official_texts():
    assert SYSTEM_PROMPT == EXPECTED_SYSTEM
    assert USER_TEMPLATE == EXPECTED_USER_TEMPLATE


def test_build_messages_exact_official_texts():
    question = "다음 중 맞는 것은? (A) 가 (B) 나"
    messages = build_messages(question)
    assert messages == [
        {"role": "system", "content": EXPECTED_SYSTEM},
        {
            "role": "user",
            "content": EXPECTED_USER_TEMPLATE.replace("{question}", question),
        },
    ]
    assert "{question}" not in messages[1]["content"]
    assert question in messages[1]["content"]


def test_build_messages_custom_overrides():
    messages = build_messages("Q?", system="SYS", user_template="Q:{question}!")
    assert messages[0] == {"role": "system", "content": "SYS"}
    assert messages[1] == {"role": "user", "content": "Q:Q?!"}


def test_build_messages_from_config_uses_prompt_section():
    from kobalt_eval.config import default_run_config
    from kobalt_eval.prompts import build_messages_from_config

    cfg = default_run_config()
    assert build_messages_from_config("Q?", cfg) == build_messages("Q?")


def test_prompt_template_hash_stable():
    assert prompt_template_hash() == prompt_template_hash()
    assert prompt_template_hash(SYSTEM_PROMPT, USER_TEMPLATE) == prompt_template_hash()


def test_prompt_template_hash_changes_with_template():
    assert prompt_template_hash(SYSTEM_PROMPT, "other {question}") != prompt_template_hash()
    assert prompt_template_hash("other system", USER_TEMPLATE) != prompt_template_hash()
