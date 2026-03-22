# ── Drug-food interaction dictionary ────────────────────────────────────────
# Key   = medication name (lowercase)
# Value = list of foods/ingredients to flag if found in a recipe

INTERACTIONS = {
    "warfarin":     ["spinach", "kale", "grapefruit", "broccoli", "parsley",
                     "green tea", "cranberry"],
    "metformin":    [],  # no major food interactions
    "statins":      ["grapefruit", "pomelo", "red yeast rice"],
    "levothyroxine":["soy", "walnuts", "high fiber", "calcium"],
    "lisinopril":   ["banana", "orange", "potato", "spinach"],   # high potassium
    "warfarin":     ["spinach", "kale", "grapefruit", "broccoli"],
    "aspirin":      ["alcohol", "ginger", "garlic", "fish oil"],
    "methotrexate": ["alcohol", "folic acid"],
    "mao_inhibitor":["aged cheese", "cured meat", "soy sauce",
                     "red wine", "beer", "yeast extract"],
}


def check_interactions(plan: dict, medications: list) -> list:
    """
    Scans every recipe in the generated meal plan against the
    drug-food interaction dictionary.

    Returns a list of warning strings — empty list means no conflicts.
    """
    if not medications:
        return []

    warnings = []

    for day, meals in plan.items():
        for meal_slot, details in meals.items():
            recipe_text = details.get("recipe", "").lower()

            for med in medications:
                med_clean = med.strip().lower()
                bad_foods = INTERACTIONS.get(med_clean, [])

                for food in bad_foods:
                    if food in recipe_text:
                        warnings.append(
                            f"⚠ Day {day} · {meal_slot.title()}: "
                            f"'{details['recipe']}' may interact with "
                            f"{med} (contains {food})"
                        )

    return warnings


def get_foods_to_avoid(medications: list) -> list:
    """
    Returns a flat list of all foods the user should avoid
    based on their medications. Used by the retriever to
    pre-filter recipes before semantic search.
    """
    avoid = []
    for med in medications:
        med_clean = med.strip().lower()
        avoid.extend(INTERACTIONS.get(med_clean, []))
    return list(set(avoid))  # remove duplicates