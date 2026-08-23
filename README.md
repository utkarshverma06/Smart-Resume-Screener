# Smart-Resume-Screener
Deployed Link: https://utkarshverma06.github.io/Smart-Resume-Screener/templates/index.html


## What it does
1. Paste or upload a job description.
2. Upload a resume (.pdf or .txt).
3. Get a 1-10 fit score with a justification and matched/missing skills.

## Run it
```bash
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Files
- `app.py` — Flask backend: resume parsing, scoring (LLM + fallback), JSON-file storage
- `templates/index.html` — single-page UI
- `sample_data/` — sample job description + resume to try it immediately
- `candidates.json` — created automatically to store scored candidates

## Image shows shortlisted only (With threshold value as per our need, we can set our own threshold value)


<img width="400" height="500" alt="Screenshot 2026-08-23 223557" src="https://github.com/user-attachments/assets/197aa38a-db16-44ed-8e9a-2f63f600f17f" />


## Image shows all the candidates (Irrespective of any threshold value)


<img width="400" height="500" alt="image" src="https://github.com/user-attachments/assets/40ce0b31-b783-4718-a0d4-23a2a833fcb5" />
