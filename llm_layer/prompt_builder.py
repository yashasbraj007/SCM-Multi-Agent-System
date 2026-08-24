"""
LLM Layer - Prompt Builder

Turns Agent 1's severity output and Agent 2's recovery output into a
natural-language prompt for the LLM, using in-context learning: two
worked examples are embedded directly in the prompt so the model learns
the target explanation style and tone without any fine-tuning.

Two prompt shapes are exposed:
- build_chat_messages()      -> single-turn explanation (LOW / MEDIUM cases)
- build_multiturn_messages() -> two connected turns for HIGH severity cases,
                                 used by llm_explainer.generate_multiturn_explanation
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RecoveryOptionSummary:
    source_type: str
    source_id: str
    estimated_delivery_days: float
    score: float


@dataclass
class DisruptionSummary:
    order_id: str
    company_name: str
    product: str
    delay_days: float
    buffer_days: float
    severity: str  # "LOW" | "MEDIUM" | "HIGH"
    best_option: Optional[RecoveryOptionSummary] = None
    all_options: List[RecoveryOptionSummary] = field(default_factory=list)


SYSTEM_INSTRUCTIONS = (
    "You are a supply chain communications assistant. You are given the "
    "structured output of two rule-based systems: Agent 1 (calculates a "
    "shelf-life/delay buffer and severity) and Agent 2 (finds recovery "
    "options such as warehouses or producers). Your only job is to explain "
    "these numbers to a human supply chain manager in plain, concise "
    "English. Do not invent numbers you were not given. Do not change the "
    "severity or recommend a different recovery option than the one "
    "provided. Keep answers to 2-4 sentences unless told otherwise."
)

# Two worked in-context examples: one LOW severity (no recovery needed),
# one HIGH severity (recovery option required). Shown to the model right
# before its own task so it can copy the tone/format without fine-tuning.
FEW_SHOT_EXAMPLES = """### Example 1
Input:
- Order: ORD-1042 (customer: GreenField Mills)
- Product: Wheat
- Delay: 2 days
- Buffer remaining after delay: 12 days
- Severity: LOW
- Recovery option: None needed

Output:
The shipment for GreenField Mills (order ORD-1042) is running 2 days behind schedule, but the wheat still has 12 days of shelf life left after accounting for the delay. That's a comfortable margin, so no recovery action is needed - the order is expected to arrive in good condition well within the customer's window.

### Example 2
Input:
- Order: ORD-2087 (customer: Prairie Bakehouse Co.)
- Product: Barley
- Delay: 9 days
- Buffer remaining after delay: -4 days
- Severity: HIGH
- Recovery option: producer PROD-014, ETA 3.2 days, score 4.8

Output:
The shipment for Prairie Bakehouse Co. (order ORD-2087) is delayed by 9 days, which pushes it 4 days past barley's safe shelf-life window - a high risk of spoilage or a missed delivery if nothing changes. To cover this, producer PROD-014 has been identified as the best recovery source, able to deliver in about 3.2 days, well ahead of the remaining tolerance. We recommend activating this recovery option immediately.
"""


def _format_option(opt: Optional[RecoveryOptionSummary]) -> str:
    if not opt:
        return "None needed"
    return f"{opt.source_type} {opt.source_id}, ETA {opt.estimated_delivery_days:.1f} days, score {opt.score}"


def _case_input_block(summary: DisruptionSummary) -> str:
    return (
        f"- Order: {summary.order_id} (customer: {summary.company_name})\n"
        f"- Product: {summary.product}\n"
        f"- Delay: {summary.delay_days} days\n"
        f"- Buffer remaining after delay: {summary.buffer_days} days\n"
        f"- Severity: {summary.severity}\n"
        f"- Recovery option: {_format_option(summary.best_option)}\n"
    )


def build_explanation_prompt(summary: DisruptionSummary) -> str:
    """
    Raw-string version: system instructions + two worked examples + the
    real case, ending on "Output:" so a plain (non-chat) model continues
    directly with the explanation text.
    """
    case_block = f"### Your turn\nInput:\n{_case_input_block(summary)}\nOutput:"
    return f"{SYSTEM_INSTRUCTIONS}\n\n{FEW_SHOT_EXAMPLES}\n{case_block}"


def build_chat_messages(summary: DisruptionSummary) -> list:
    """
    Same content as build_explanation_prompt, split into chat roles for
    instruction-tuned models (e.g. Qwen2.5-Instruct) that expect a chat
    template rather than a single raw string.
    """
    case_block = f"### Your turn\nInput:\n{_case_input_block(summary)}\nOutput:"
    user_content = f"{FEW_SHOT_EXAMPLES}\n{case_block}"
    return [
        {"role": "system", "content": SYSTEM_INSTRUCTIONS},
        {"role": "user", "content": user_content},
    ]


def build_multiturn_messages(summary: DisruptionSummary) -> dict:
    """
    For HIGH severity cases: builds two connected user turns that simulate
    a back-and-forth between Agent 1's risk read and Agent 2's recovery
    plan, instead of a single one-shot explanation.

    Turn 1 only sees Agent 1's numbers (severity/buffer) and states the
    risk. Turn 2 is answered by the same model *after* its own turn-1
    answer is fed back in as chat history, together with Agent 2's ranked
    options, and asks for a final recommendation that references turn 1.
    The chaining (turn-1 answer -> turn-2 context) is what makes this
    multi-turn reasoning rather than two independent single-shot calls.
    """
    turn1_user = (
        f"{FEW_SHOT_EXAMPLES}\n"
        f"### Turn 1 - Risk assessment only (Agent 1's data)\n"
        f"Input:\n"
        f"- Order: {summary.order_id} (customer: {summary.company_name})\n"
        f"- Product: {summary.product}\n"
        f"- Delay: {summary.delay_days} days\n"
        f"- Buffer remaining after delay: {summary.buffer_days} days\n"
        f"- Severity: {summary.severity}\n\n"
        f"Explain the risk to this order in 2-3 sentences. Do not mention "
        f"any recovery option yet - none has been decided at this point."
    )

    if summary.all_options:
        options_lines = "\n".join(
            f"  {i + 1}. {o.source_type} {o.source_id}, ETA {o.estimated_delivery_days:.1f} days, score {o.score}"
            for i, o in enumerate(summary.all_options)
        )
    else:
        options_lines = "  (no viable recovery options were found)"

    best_label = (
        f"{summary.best_option.source_type} {summary.best_option.source_id}"
        if summary.best_option else "no option"
    )

    turn2_user = (
        f"### Turn 2 - Recovery decision (Agent 2's data)\n"
        f"Given the risk you just described, Agent 2 searched the warehouse "
        f"and producer network and found these candidates, ranked best "
        f"(lowest score) first:\n{options_lines}\n\n"
        f"Referencing the risk from your last answer, explain in 2-4 "
        f"sentences why {best_label} is the right recovery choice, and "
        f"what happens if it is not actioned quickly."
    )

    return {"turn1_user": turn1_user, "turn2_user": turn2_user}


if __name__ == "__main__":
    # Quick offline check of the prompt formatting - no model/GPU needed.
    demo_low = DisruptionSummary(
        order_id="ORD-3001", company_name="Test Co.", product="Wheat",
        delay_days=2, buffer_days=12, severity="LOW",
    )
    demo_high = DisruptionSummary(
        order_id="ORD-3002", company_name="Test Co.", product="Rice",
        delay_days=15, buffer_days=-6, severity="HIGH",
        best_option=RecoveryOptionSummary("warehouse", "WH-007", 4.0, 3.1),
        all_options=[
            RecoveryOptionSummary("warehouse", "WH-007", 4.0, 3.1),
            RecoveryOptionSummary("producer", "PROD-022", 6.5, 9.4),
        ],
    )

    print("=== single-turn chat messages (LOW) ===")
    for m in build_chat_messages(demo_low):
        print(f"[{m['role']}]\n{m['content']}\n")

    print("=== multi-turn messages (HIGH) ===")
    turns = build_multiturn_messages(demo_high)
    print("--- turn 1 ---\n", turns["turn1_user"])
    print("\n--- turn 2 ---\n", turns["turn2_user"])
