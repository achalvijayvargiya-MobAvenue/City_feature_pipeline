# USA City Features Pipeline

This project is a modular, spec-driven data engineering pipeline designed to generate a 36-column USA city features dataset. It replaces the fuzzy-matching and hardcoded lists of the India pipeline with authoritative government APIs (Census, FAA, BLS) and deterministic spatial joins.

## Getting Started

1. **Read the Spec:** Before writing any code, read the full specification in `Source/USA_City_Features_SDD/USA_CITY_FEATURES_SDD.md`.
2. **Setup Environment:**
   ```bash
   cd USA
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e .
   ```
3. **Team Tasks:** If you are a team member contributing to this project, please see [docs/TEAM_TASKS.md](docs/TEAM_TASKS.md) for your specific assignments and step-by-step implementation guides.
