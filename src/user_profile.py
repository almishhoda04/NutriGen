from pydantic import BaseModel
from typing import List

# ── Activity multipliers (Mifflin-St Jeor) ──────────────────────────────────
ACTIVITY_MULT = {
    "sedentary": 1.2,
    "light":     1.375,
    "moderate":  1.55,
    "active":    1.725,
}

# ── Calorie adjustment based on goal ────────────────────────────────────────
GOAL_ADJUST = {
    "weight_loss":  -500,
    "muscle_gain":  +300,
    "maintain":       0,
}

# ── Query modifiers for health conditions (used in retriever later) ──────────
CONDITION_MODIFIERS = {
    "diabetes_type2": "low glycemic low sugar no refined carbs",
    "hypertension":   "low sodium low salt",
    "pcos":           "low carb anti-inflammatory high fiber",
    "hypothyroid":    "selenium rich avoid raw goitrogens",
    "ibs":            "low fodmap easy to digest gentle",
    "high_cholesterol": "low saturated fat heart healthy",
}


class UserProfile(BaseModel):
    name:               str
    age:                int
    gender:             str            # "male" or "female"
    weight_kg:          float
    height_cm:          float
    activity_level:     str            # sedentary / light / moderate / active
    goal:               str            # weight_loss / muscle_gain / maintain
    health_conditions:  List[str]      # e.g. ["diabetes_type2", "hypertension"]
    intolerances:       List[str]      # e.g. ["gluten", "lactose", "nuts"]
    cuisine_preference: List[str]      # e.g. ["Indian", "Mediterranean"]
    meal_prep_time:     int            # max minutes per meal
    meals_per_day:      int            # 3 or 5
    medications:        List[str] = [] # optional e.g. ["warfarin", "metformin"]

    def calculate_bmr(self) -> float:
        """Mifflin-St Jeor equation"""
        if self.gender.lower() == "male":
            return 10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age + 5
        else:
            return 10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age - 161

    def calculate_targets(self) -> dict:
        """Returns daily calorie + macro targets"""
        bmr  = self.calculate_bmr()
        tdee = bmr * ACTIVITY_MULT[self.activity_level]
        target_cal = tdee + GOAL_ADJUST[self.goal]

        return {
            "calories":  round(target_cal),
            "protein_g": round(self.weight_kg * 2.0),        # 2g per kg bodyweight
            "carbs_g":   round(target_cal * 0.45 / 4),       # 45% of calories from carbs
            "fat_g":     round(target_cal * 0.25 / 9),       # 25% of calories from fat
        }

    def get_condition_query_modifiers(self) -> str:
        """Returns a string of search modifiers based on health conditions"""
        modifiers = []
        for condition in self.health_conditions:
            if condition in CONDITION_MODIFIERS:
                modifiers.append(CONDITION_MODIFIERS[condition])
        return " ".join(modifiers)