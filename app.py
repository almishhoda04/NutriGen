# app.py

import streamlit as st
import json
import sys
import os
import os
if not os.path.exists("data/chroma_db"):
    from src.knowledge_base import build_knowledge_base
    build_knowledge_base()

sys.path.insert(0, os.path.abspath("."))

from src.user_profile import UserProfile
from src.meal_planner import generate_meal_plan
from src.chat_agent import chat
from src.drug_food import check_interactions

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NutriGen",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #f7f4ef; }
    .block-container { padding-top: 2rem; }
    .meal-card {
        background: white;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 10px;
        border-left: 4px solid #2d6a4f;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .meal-slot { font-size: 11px; color: #888; text-transform: uppercase;
                 letter-spacing: 1px; margin-bottom: 2px; }
    .meal-name { font-size: 15px; font-weight: 700; color: #1a1a14; }
    .meal-cal  { font-size: 12px; color: #2d6a4f; margin-top: 3px; }
    .meal-note { font-size: 12px; color: #888; font-style: italic; }
    .target-box {
        background: #2d6a4f; color: white;
        border-radius: 8px; padding: 16px;
        text-align: center;
    }
    .target-num  { font-size: 24px; font-weight: 800; }
    .target-label{ font-size: 11px; opacity: 0.7; text-transform: uppercase;
                   letter-spacing: 1px; }
    .warning-box {
        background: #fff3cd; border-left: 4px solid #f59e0b;
        padding: 12px 16px; border-radius: 4px; margin: 8px 0;
        font-size: 13px;
    }
    .section-title {
        font-size: 22px; font-weight: 800; color: #1a1a14;
        margin-bottom: 4px;
    }
    .section-sub { font-size: 13px; color: #888; margin-bottom: 20px; }
    div[data-testid="stChatMessage"] { background: white !important;
        border-radius: 8px; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)


# ── Session state initialisation ──────────────────────────────────────────────
if "page"         not in st.session_state: st.session_state.page         = "profile"
if "profile"      not in st.session_state: st.session_state.profile      = None
if "meal_plan"    not in st.session_state: st.session_state.meal_plan    = None
if "targets"      not in st.session_state: st.session_state.targets      = None
if "warnings"     not in st.session_state: st.session_state.warnings     = []
if "chat_history" not in st.session_state: st.session_state.chat_history = []


# ════════════════════════════════════════════════════════════════════════════
# PAGE 1 — PROFILE FORM
# ════════════════════════════════════════════════════════════════════════════
def show_profile_page():

    # Header
    st.markdown("""
        <div style='text-align:center; padding: 20px 0 10px'>
            <div style='font-size:42px'>🥗</div>
            <div style='font-size:32px; font-weight:900; color:#1a1a14'>NutriGen</div>
            <div style='font-size:14px; color:#888; margin-top:4px'>
                Personalized AI meal planning for busy professionals
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Tell us about yourself")

    # ── Row 1: Basic info ─────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        name   = st.text_input("Your Name", placeholder="e.g. Priya")
        age    = st.slider("Age", 18, 70, 25)
    with c2:
        gender = st.radio("Gender", ["female", "male"], horizontal=True)
        weight = st.number_input("Weight (kg)", 35.0, 150.0, 65.0, step=0.5)
    with c3:
        height       = st.number_input("Height (cm)", 140.0, 210.0, 165.0, step=0.5)
        meals_per_day = st.radio("Meals per day", [3, 5], horizontal=True)

    st.markdown("---")

    # ── Row 2: Goals & lifestyle ──────────────────────────────────────────────
    c4, c5 = st.columns(2)
    with c4:
        activity = st.selectbox(
            "Activity Level",
            ["sedentary", "light", "moderate", "active"],
            index=1,
            help="sedentary=desk job, light=walks, moderate=gym 3x, active=gym 5x+"
        )
        goal = st.selectbox(
            "Your Goal",
            ["weight_loss", "muscle_gain", "maintain"],
            format_func=lambda x: {
                "weight_loss":  "⚖ Lose Weight",
                "muscle_gain":  "💪 Build Muscle",
                "maintain":     "🎯 Maintain Weight"
            }[x]
        )
    with c5:
        prep_time = st.slider(
            "Max meal prep time (minutes)", 10, 60, 30, step=5
        )
        cuisines = st.multiselect(
            "Cuisine Preferences",
            ["Indian", "Mediterranean", "Asian", "Continental",
             "Mexican", "Middle Eastern", "American"],
            default=["Indian"]
        )

    st.markdown("---")

    # ── Row 3: Health info ────────────────────────────────────────────────────
    c6, c7 = st.columns(2)
    with c6:
        conditions = st.multiselect(
            "Health Conditions (if any)",
            ["diabetes_type2", "hypertension", "pcos",
             "hypothyroid", "ibs", "high_cholesterol"],
            help="This helps NourishIQ tailor recipes to your needs"
        )
        medications = st.text_input(
            "Medications (comma separated, optional)",
            placeholder="e.g. warfarin, metformin"
        )
    with c7:
        intolerances = st.multiselect(
            "Food Intolerances / Allergies",
            ["gluten", "lactose", "nuts", "eggs", "soy"],
            help="These will be strictly excluded from all recommendations"
        )

    st.markdown("---")

    # ── Generate button ───────────────────────────────────────────────────────
    col_btn = st.columns([1, 2, 1])[1]
    with col_btn:
        generate = st.button(
            "🍽 Generate My 7-Day Plan",
            type="primary",
            use_container_width=True
        )

    if generate:
        if not name:
            st.error("Please enter your name.")
            return
        if not cuisines:
            st.warning("Please select at least one cuisine preference.")
            return

        # Parse medications
        meds = [m.strip() for m in medications.split(",") if m.strip()] \
               if medications else []

        # Build profile
        profile = UserProfile(
            name               = name,
            age                = age,
            gender             = gender,
            weight_kg          = weight,
            height_cm          = height,
            activity_level     = activity,
            goal               = goal,
            health_conditions  = conditions,
            intolerances       = intolerances,
            cuisine_preference = cuisines,
            meal_prep_time     = prep_time,
            meals_per_day      = meals_per_day,
            medications        = meds,
        )

        # Generate plan with spinner
        with st.spinner("🧠 NutriGen is building your personalized plan..."):
            plan    = generate_meal_plan(profile)
            targets = profile.calculate_targets()
            warnings = check_interactions(plan, meds)

        if plan:
            st.session_state.profile      = profile
            st.session_state.meal_plan    = plan
            st.session_state.targets      = targets
            st.session_state.warnings     = warnings
            st.session_state.chat_history = []
            st.session_state.page         = "plan"
            st.rerun()
        else:
            st.error("Something went wrong generating the plan. Please try again.")


# ════════════════════════════════════════════════════════════════════════════
# PAGE 2 — MEAL PLAN + CHAT
# ════════════════════════════════════════════════════════════════════════════
def show_plan_page():
    profile  = st.session_state.profile
    plan     = st.session_state.meal_plan
    targets  = st.session_state.targets
    warnings = st.session_state.warnings

    # ── Top bar ───────────────────────────────────────────────────────────────
    c_title, c_back = st.columns([5, 1])
    with c_title:
        st.markdown(f"""
            <div class='section-title'>🥗 {profile.name}'s 7-Day Plan</div>
            <div class='section-sub'>
                {profile.goal.replace('_',' ').title()} · 
                {', '.join(profile.cuisine_preference)} cuisine · 
                {profile.meal_prep_time} min max prep
            </div>
        """, unsafe_allow_html=True)
    with c_back:
        if st.button("← Edit Profile"):
            st.session_state.page = "profile"
            st.rerun()

    # ── Daily targets ─────────────────────────────────────────────────────────
    t1, t2, t3, t4 = st.columns(4)
    for col, label, value in zip(
        [t1, t2, t3, t4],
        ["Daily Calories", "Protein", "Carbohydrates", "Fat"],
        [f"{targets['calories']} kcal",
         f"{targets['protein_g']}g",
         f"{targets['carbs_g']}g",
         f"{targets['fat_g']}g"]
    ):
        with col:
            st.markdown(f"""
                <div class='target-box'>
                    <div class='target-num'>{value}</div>
                    <div class='target-label'>{label}</div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Drug-food warnings ────────────────────────────────────────────────────
    if warnings:
        st.markdown("#### ⚠ Drug-Food Interaction Warnings")
        for w in warnings:
            st.markdown(f"<div class='warning-box'>{w}</div>",
                        unsafe_allow_html=True)

    # ── Meal plan display ─────────────────────────────────────────────────────
    st.markdown("#### 📅 Your Week")

    # Show 7 days in rows of 2 columns
    days = list(plan.items())
    for i in range(0, len(days), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j >= len(days):
                break
            day_key, meals = days[i + j]
            day_label = day_key.replace("_", " ").title()
            with col:
                with st.expander(f"📅 {day_label}", expanded=(i + j == 0)):
                    for slot, details in meals.items():
                        recipe  = details.get("recipe",  "—")
                        cal     = details.get("calories", "?")
                        note    = details.get("note",    "")
                        st.markdown(f"""
                            <div class='meal-card'>
                                <div class='meal-slot'>{slot}</div>
                                <div class='meal-name'>{recipe}</div>
                                <div class='meal-cal'>~{cal} kcal</div>
                                <div class='meal-note'>{note}</div>
                            </div>
                        """, unsafe_allow_html=True)

    # ── Chat section ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 💬 Adjust Your Plan")
    st.markdown(
        "<div class='section-sub'>Ask questions or request changes — "
        "e.g. 'Replace Thursday dinner, I don't like fish' or "
        "'Which day has the most protein?'</div>",
        unsafe_allow_html=True
    )

    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Chat input
    user_input = st.chat_input("Ask NutriGen anything about your plan...")

    if user_input:
        # Show user message
        st.session_state.chat_history.append({
            "role": "user", "content": user_input
        })

        with st.spinner("NutriGen is thinking..."):
            response, updated_plan = chat(
                user_input,
                st.session_state.meal_plan,
                profile
            )

        # Update plan if it changed
        st.session_state.meal_plan = updated_plan

        # Show assistant response
        st.session_state.chat_history.append({
            "role": "assistant", "content": response
        })

        st.rerun()

    # ── Download plan ─────────────────────────────────────────────────────────
    st.markdown("---")
    plan_json = json.dumps(st.session_state.meal_plan, indent=2)
    st.download_button(
        label="⬇ Download My Plan (JSON)",
        data=plan_json,
        file_name=f"NutriGen_plan_{profile.name.lower()}.json",
        mime="application/json"
    )


# ════════════════════════════════════════════════════════════════════════════
# ROUTER
# ════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "profile":
    show_profile_page()
else:
    show_plan_page()