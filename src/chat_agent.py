# src/chat_agent.py

import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from src.user_profile import UserProfile

load_dotenv()

# ── LLM setup ────────────────────────────────────────────────────────────────
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.5,
)

# ── Detect if user wants to modify the plan or just ask a question ────────────
MODIFICATION_KEYWORDS = [
    "replace", "change", "swap", "remove", "substitute",
    "different", "instead", "don't like", "hate", "avoid",
    "add", "include", "give me", "update", "modify"
]

def is_modification_request(message: str) -> bool:
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in MODIFICATION_KEYWORDS)


def adjust_plan(user_message: str, current_plan: dict, profile: UserProfile) -> dict:
    """
    Takes the user's modification request and returns an updated plan JSON.
    The entire current plan is passed so the LLM only changes what's needed.
    """
    prompt = f"""You are NutriGen, a personal nutritionist AI.
The user wants to modify their meal plan.

CURRENT MEAL PLAN:
{json.dumps(current_plan, indent=2)}

USER PROFILE CONSTRAINTS (always respect these):
- Intolerances (never include): {', '.join(profile.intolerances) or 'none'}
- Health conditions: {', '.join(profile.health_conditions) or 'none'}
- Max prep time: {profile.meal_prep_time} minutes
- Goal: {profile.goal}

USER REQUEST: {user_message}

Instructions:
1. Only change what the user asked — keep everything else exactly the same
2. Never introduce foods that violate the user's intolerances
3. Return the COMPLETE updated plan JSON
4. Output ONLY valid JSON — no explanation, no markdown

Return the full updated plan in the same format as the current plan."""

    response = llm.invoke([("human", prompt)])
    raw = response.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # If JSON fails return original plan unchanged
        print("⚠ Could not parse updated plan — keeping original")
        return current_plan


def answer_question(user_message: str, current_plan: dict, profile: UserProfile) -> str:
    """
    Answers questions about the plan without modifying it.
    e.g. 'Why is Tuesday lunch good for me?' or 'What's my protein on day 3?'
    """
    prompt = f"""You are NutriGen, a personal nutritionist AI.
Answer the user's question about their meal plan.

CURRENT MEAL PLAN:
{json.dumps(current_plan, indent=2)}

USER PROFILE:
- Goal: {profile.goal}
- Health conditions: {', '.join(profile.health_conditions) or 'none'}
- Daily calorie target: {profile.calculate_targets()['calories']} kcal
- Daily protein target: {profile.calculate_targets()['protein_g']}g

USER QUESTION: {user_message}

Answer helpfully and concisely in 2-4 sentences. Be specific — reference actual 
recipes and numbers from the plan where relevant."""

    response = llm.invoke([("human", prompt)])
    return response.content.strip()


def chat(user_message: str, current_plan: dict, profile: UserProfile):
    """
    Main chat function — routes to modify or answer based on message type.
    Returns: (response_text, updated_plan)
    """
    if is_modification_request(user_message):
        print("  → Detected modification request")
        updated_plan = adjust_plan(user_message, current_plan, profile)
        # Find what changed to show the user
        response_text = "✓ I've updated your meal plan based on your request."
        return response_text, updated_plan
    else:
        print("  → Detected question")
        answer = answer_question(user_message, current_plan, profile)
        return answer, current_plan  # plan unchanged


# ── Run directly to test ──────────────────────────────────────────────────────
if __name__ == "__main__":
    from src.meal_planner import generate_meal_plan

    print("=" * 60)
    print("NutriGen — Chat Agent Test")
    print("=" * 60)

    # Use same test profile
    profile = UserProfile(
        name="Priya", age=35, gender="female",
        weight_kg=62, height_cm=160,
        activity_level="light", goal="weight_loss",
        health_conditions=["diabetes_type2"],
        intolerances=["lactose"],
        cuisine_preference=["Indian", "Mediterranean"],
        meal_prep_time=30, meals_per_day=3,
    )

    # Load saved plan from meal_planner test
    try:
        with open("data/test_plan.json", "r") as f:
            plan = json.load(f)
        print("✓ Loaded existing test plan\n")
    except FileNotFoundError:
        print("Generating plan first...")
        plan = generate_meal_plan(profile)

    # Test 1 — modification request
    print("TEST 1 — Modification request")
    print("User: 'Replace day 1 dinner, I don't like chicken'")
    response, updated_plan = chat(
        "Replace day 1 dinner, I don't like chicken",
        plan, profile
    )
    print(f"NutriGen: {response}")
    print(f"Day 1 dinner is now: {updated_plan.get('day_1', {}).get('dinner', {}).get('recipe', '?')}")

    print("\n" + "-" * 40)

    # Test 2 — question
    print("\nTEST 2 — Question")
    print("User: 'Which day has the most protein?'")
    response, _ = chat(
        "Which day has the most protein?",
        plan, profile
    )
    print(f"NutriGen: {response}")

    print("\n" + "-" * 40)

    # Test 3 — another question
    print("\nTEST 3 — Question about conditions")
    print("User: 'Why is this plan good for my diabetes?'")
    response, _ = chat(
        "Why is this plan good for my diabetes?",
        plan, profile
    )
    print(f"NutriGen: {response}")
