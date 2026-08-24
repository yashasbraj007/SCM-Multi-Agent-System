"""
LLM Layer - Explainer

Loads a small instruction-tuned model (Qwen2.5-1.5B-Instruct) in plain
float32 and runs it on CPU - no GPU/CUDA/bitsandbytes required. This is
the CPU-friendly counterpart to a GPU 4-bit setup: a 1.5B model is small
enough to run comfortably on a laptop CPU (a few seconds to ~30s per
explanation, depending on hardware), while still being an instruction-
tuned chat model good enough for the in-context-learning prompts from
prompt_builder.py.

If you do have an NVIDIA GPU available (e.g. via Colab), you can swap
MODEL_NAME to "Qwen/Qwen2.5-3B-Instruct" and add a BitsAndBytesConfig
4-bit quantization_config to _load_model() for a stronger model - the
rest of this module (prompt building, single-turn vs multi-turn) doesn't
need to change.

The model/tokenizer are loaded once (lazy singleton) and reused across
calls, since loading takes several seconds and repeating it per-disruption
would be wasteful.
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

try:
    from .prompt_builder import build_chat_messages, build_multiturn_messages, SYSTEM_INSTRUCTIONS
except ImportError:  # allows `python llm_explainer.py` / sys.path-based imports too
    from prompt_builder import build_chat_messages, build_multiturn_messages, SYSTEM_INSTRUCTIONS

# Qwen2.5-1.5B-Instruct: good quality/speed balance on CPU (~3GB RAM in
# float32). Drop to "Qwen/Qwen2.5-0.5B-Instruct" for a faster/lighter
# model if generation feels too slow on your machine.
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"

_tokenizer = None
_model = None


def _load_model():
    """Lazily loads (once) the model + tokenizer, on CPU."""
    global _tokenizer, _model
    if _model is not None:
        return _tokenizer, _model

    _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    _model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype=torch.float32)
    _model.to("cpu")
    _model.eval()
    return _tokenizer, _model


def _generate_from_messages(tokenizer, model, messages: list, max_new_tokens: int) -> str:
    prompt_text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.4,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
        )

    generated = output_ids[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(generated, skip_special_tokens=True).strip()


def generate_explanation(summary, max_new_tokens: int = 200) -> str:
    """
    Single-turn explanation for LOW / MEDIUM severity cases.
    `summary` is a prompt_builder.DisruptionSummary.
    """
    tokenizer, model = _load_model()
    messages = build_chat_messages(summary)
    return _generate_from_messages(tokenizer, model, messages, max_new_tokens)


def generate_multiturn_explanation(summary, max_new_tokens: int = 200) -> dict:
    """
    Two-turn conversation for HIGH severity cases: turn 1 gets the model to
    state the risk from Agent 1's numbers alone, turn 2 feeds that answer
    back in as real chat history along with Agent 2's ranked options and
    asks for the final recovery recommendation. This is the "multi-turn
    reasoning between the two agents" orchestrator.py uses for HIGH cases.

    Returns {"risk_analysis": <turn 1 text>, "final_recommendation": <turn 2 text>}.
    """
    tokenizer, model = _load_model()
    turns = build_multiturn_messages(summary)

    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTIONS},
        {"role": "user", "content": turns["turn1_user"]},
    ]
    risk_analysis = _generate_from_messages(tokenizer, model, messages, max_new_tokens=150)

    messages.append({"role": "assistant", "content": risk_analysis})
    messages.append({"role": "user", "content": turns["turn2_user"]})
    final_recommendation = _generate_from_messages(tokenizer, model, messages, max_new_tokens=max_new_tokens)

    return {"risk_analysis": risk_analysis, "final_recommendation": final_recommendation}


if __name__ == "__main__":
    # Manual smoke test - downloads the model (~3GB in float32) on first
    # run, then generates on CPU. Not run automatically in CI/sandboxes.
    try:
        from .prompt_builder import DisruptionSummary, RecoveryOptionSummary
    except ImportError:
        from prompt_builder import DisruptionSummary, RecoveryOptionSummary

    demo = DisruptionSummary(
        order_id="ORD-3001", company_name="Test Co.", product="Wheat",
        delay_days=2, buffer_days=12, severity="LOW",
    )
    print(generate_explanation(demo))
