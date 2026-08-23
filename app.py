import json
import os
import re
from pathlib import Path
from flask import Flask, jsonify, render_template, request
from pypdf import PdfReader

app = Flask(__name__)
DB_FILE = Path(__file__).parent / "candidates.json"

SKILLS_VOCAB = [
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "sql",
    "postgresql", "mongodb", "react", "node.js", "django", "flask", "fastapi",
    "aws", "azure", "gcp", "docker", "kubernetes", "ci/cd", "machine learning",
    "nlp", "pytorch", "tensorflow", "pandas", "git", "rest api", "agile",
    "html", "css", "linux",
]

# ---------- storage (a plain JSON file — no ORM, easy to read) ----------
def load_candidates():
    if DB_FILE.exists():
        return json.loads(DB_FILE.read_text())
    return []
def save_candidates(candidates):
    DB_FILE.write_text(json.dumps(candidates, indent=2))

# ---------- resume parsing ----------
def extract_text(file_storage):
    filename = file_storage.filename.lower()
    if filename.endswith(".pdf"):
        reader = PdfReader(file_storage)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return file_storage.read().decode(errors="ignore")
def extract_skills(text):
    text = text.lower()
    return sorted({s for s in SKILLS_VOCAB if s in text})
def extract_years_experience(text):
    matches = re.findall(r"(\d+)\+?\s*(?:years|yrs)", text.lower())
    return max((int(m) for m in matches), default=0)

# ---------- scoring ----------
def score_with_keywords(resume_text, jd_text):
    """No-API-key fallback: score by how many JD-mentioned skills appear in the resume."""
    jd_skills = extract_skills(jd_text)
    resume_skills = extract_skills(resume_text)
    matched = sorted(set(jd_skills) & set(resume_skills))
    missing = sorted(set(jd_skills) - set(resume_skills))
    if jd_skills:
        score = round((len(matched) / len(jd_skills)) * 10)
    else:
        score = 5  # JD mentioned no recognizable skills — can't judge, give a neutral score
    justification = (
        f"Matched {len(matched)} of {len(jd_skills)} skills mentioned "
        f"in the job description."
    )
    return {
        "score": max(1, score),
        "justification": justification,
        "matched_skills": matched,
        "missing_skills": missing,
        "method": "keyword_fallback",
    }
def score_with_llm(resume_text, jd_text):
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = f"""Compare the following resume with this job description and rate fit on 1-10 with justification.
JOB DESCRIPTION:
{jd_text}
RESUME:
{resume_text[:4000]}
Respond with ONLY this JSON, no markdown fences, no extra text:
{{"score": <1-10 integer>, "justification": "<2-3 sentences>", "matched_skills": ["..."], "missing_skills": ["..."]}}
"""
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    text = re.sub(r"^```(json)?|```$", "", text, flags=re.MULTILINE).strip()
    result = json.loads(text)
    result["method"] = "llm"
    return result
def score_resume(resume_text, jd_text):
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return score_with_llm(resume_text, jd_text)
        except Exception:
            return score_with_keywords(resume_text, jd_text)
    return score_with_keywords(resume_text, jd_text)

# ---------- routes ----------
@app.route("/")
def index():
    return render_template("index.html")
@app.route("/api/score", methods=["POST"])
def api_score():
    jd_text = request.form.get("job_description", "").strip()
    jd_file = request.files.get("job_description_file")
    file = request.files.get("resume")
    if jd_file and jd_file.filename:
        if not jd_file.filename.lower().endswith((".pdf", ".txt")):
            return jsonify({"error": "Job description file must be .pdf or .txt."}), 400
        try:
            jd_text = extract_text(jd_file).strip()
        except Exception as e:
            return jsonify({"error": f"Could not read the job description file: {e}"}), 400
    if not jd_text:
        return jsonify({"error": "Job description is required (paste text or upload a file)."}), 400
    if not file or not file.filename:
        return jsonify({"error": "A resume file is required."}), 400
    if not file.filename.lower().endswith((".pdf", ".txt")):
        return jsonify({"error": "Only .pdf or .txt resumes are supported."}), 400
    try:
        resume_text = extract_text(file)
    except Exception as e:
        return jsonify({"error": f"Could not read the file: {e}"}), 400
    if not resume_text.strip():
        return jsonify({"error": "No text could be extracted from that file (is it a scanned/image PDF?)."}), 400
    result = score_resume(resume_text, jd_text)
    candidate = {
        "filename": file.filename,
        "skills": extract_skills(resume_text),
        "experience_years": extract_years_experience(resume_text),
        **result,
    }
    candidates = load_candidates()
    candidates.append(candidate)
    candidates.sort(key=lambda c: c["score"], reverse=True)
    save_candidates(candidates)
    return jsonify({"new_candidate": candidate, "all_candidates": candidates})
@app.route("/api/candidates")
def api_candidates():
    return jsonify(load_candidates())
@app.route("/api/reset", methods=["POST"])
def api_reset():
    save_candidates([])
    return jsonify({"ok": True})
if __name__ == "__main__":
    app.run(debug=True, port=5000)