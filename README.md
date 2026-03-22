# 🥗 NutriGen — Personalized AI Meal Planning Tool

NutriGen is an AI-powered meal planning tool that generates personalized 7-day meal plans for busy professionals based on their health conditions, dietary intolerances, fitness goals, and cuisine preferences.

Built as a portfolio project demonstrating end-to-end ML engineering — from data collection and vector embeddings to RAG-based retrieval and LLM generation.

---

## Demo

> Fill in your profile → get a personalized 7-day plan in ~40 seconds → chat to adjust it

---

## Features

- **Personalized Meal Plans** — 7-day plans generated based on BMR/TDEE calculations, health conditions, and fitness goals
- **Constraint-Aware Retrieval** — RAG pipeline filters recipes by intolerances, prep time, and calorie targets before semantic search
- **Health Condition Support** — diabetes, hypertension, PCOS, hypothyroidism, IBS, high cholesterol
- **Drug-Food Interaction Checker** — flags recipes that may interact with user medications
- **Conversational Adjustment** — chat with NutriGen to swap meals, ask questions, or modify the plan
- **200+ Recipe Knowledge Base** — built from Spoonacular API, embedded with sentence-transformers

---

## System Architecture
```
User Profile Form
      ↓
Profile Engine (BMR → TDEE → Macro Targets)
      ↓
Constraint Filter (intolerances + prep time + calories + drug interactions)
      ↓
Semantic Retriever (ChromaDB + all-MiniLM-L6-v2)
      ↓
LLM Meal Plan Generator (Groq + Llama-3.3-70b)
      ↓
7-Day Plan + Chat Adjustment
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector Store | ChromaDB (persistent, local) |
| LLM | Llama-3.3-70b-versatile via Groq API |
| LLM Framework | LangChain |
| UI | Streamlit |
| Data Source | Spoonacular API |
| Validation | Pydantic |

---

## Project Structure
```
nourishiq/
├── data/
│   ├── recipes_clean.json      # 200+ cleaned recipes
│   └── chroma_db/              # persistent vector store
├── src/
│   ├── user_profile.py         # UserProfile dataclass + BMR/TDEE
│   ├── recipe_loader.py        # Spoonacular fetcher + cleaner
│   ├── knowledge_base.py       # ChromaDB builder
│   ├── retriever.py            # constraint-aware semantic retriever
│   ├── meal_planner.py         # LLM 7-day plan generator
│   ├── chat_agent.py           # conversational adjustment agent
│   └── drug_food.py            # drug-food interaction checker
├── app.py                      # Streamlit entry point
├── requirements.txt
└── .env                        # API keys (never commit)
```

---

## Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/almishhoda04/NutriGen.git
cd NutriGen
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up API keys
Create a `.env` file in the root directory:
```
GROQ_API_KEY=your_groq_key_here
SPOONACULAR_API_KEY=your_spoonacular_key_here
```

Get free keys from:
- Groq: https://console.groq.com
- Spoonacular: https://spoonacular.com/food-api

### 5. Build the knowledge base
```bash
python src/recipe_loader.py
python -m src.knowledge_base
```

### 6. Run the app
```bash
streamlit run app.py
```

---

## Key Design Decisions

**Filter → Retrieve (not Retrieve → Filter)**
Most RAG implementations retrieve first and filter after. NutriGen applies hard constraints (intolerances, prep time, calorie range) before semantic search. This ensures the LLM never even sees unsafe recipes.

**Per-day generation with exclusion tracking**
The meal planner makes 7 separate LLM calls — one per day — passing a list of already-used recipes as context. This forces variety across the week without relying on the LLM to self-manage repetition.

**Mifflin-St Jeor over Harris-Benedict**
The BMR calculation uses the Mifflin-St Jeor equation, which has been shown to be more accurate for modern populations across multiple validation studies.

**Drug-food interaction layer**
A hardcoded interaction dictionary scans the generated plan for foods contraindicated with the user's medications. This runs post-generation and surfaces warnings in the UI — adding a clinical safety layer not present in typical meal planning tools.

---

## Supported Health Conditions

| Condition | Query Modifier Applied |
|---|---|
| Type 2 Diabetes | low glycemic, low sugar, no refined carbs |
| Hypertension | low sodium, low salt |
| PCOS | low carb, anti-inflammatory, high fiber |
| Hypothyroidism | selenium rich, avoid raw goitrogens |
| IBS | low FODMAP, easy to digest |
| High Cholesterol | low saturated fat, heart healthy |

---

## Future Improvements

- [ ] Add grocery list generation from the weekly plan
- [ ] Integrate calorie tracking with daily log
- [ ] Add collaborative filtering for recipe preference learning
- [ ] Expand knowledge base to 1000+ recipes
- [ ] Add image display for each recipe
- [ ] Deploy as a web app with user authentication

---

## Author

**Almish Sohail Hoda** — B.Tech Machine Learning  
[GitHub](https://github.com/almishhoda04) · [LinkedIn](https://www.linkedin.com/in/almishhoda8928/) · [Medium](https://medium.com/@almishhoda123)
