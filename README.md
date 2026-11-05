# PriorityLens

Customer feedback triage console: your Excel/CSV feedback -> clean -> label (category + sentiment) -> RICE-ranked backlog -> dashboard.

## Files
- `generator.py` - creates a sample Excel file (100 messy rows) i made a sample one, you can use as a template
- `pipeline.py` - Step 0 load file, Step 1 clean, Step 2 label, Step 3 RICE
- `app.py` - Streamlit dashboard with a file upload button

## Your Excel file
Only one column is required: the feedback text. Name it `raw_feedback_text` (or `feedback`, `text`, `comment`, `review`, `message`).
Optional columns: `feedback_id`, `customer_id`, `source` (App Store / Support Ticket / Survey), `date`.
Other source names work too; they just get default reach and confidence values.

## How to run
1. Install Python 3.9+ (Windows: tick "Add Python to PATH").
2. Open a terminal in this folder.
3. `pip install -r requirements.txt`
4. `streamlit run app.py`
5. Browser opens at http://localhost:8501. Upload your file in the sidebar, or use the sample data.

Without the dashboard: `python pipeline.py my_feedback.xlsx`

If `streamlit` is not recognised, use `python -m streamlit run app.py`.

## Notes
- The "LLM" step is simulated with keyword rules (English only). Replace `categorize()` in `pipeline.py` to use a real LLM.
- Reach, impact, confidence and effort are editable assumptions in the RICE section of `pipeline.py`.
