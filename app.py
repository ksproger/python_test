import json
from flask import Flask, render_template, request, jsonify
import subprocess
from datetime import datetime

app = Flask(__name__)

with open("tasks.json", encoding="utf-8") as f:
    tasks = json.load(f)

progress_file = "progress.json"
log_file = "logs.txt"

def load_progress():
    with open(progress_file, encoding="utf-8") as f:
        return json.load(f)

def save_progress(p):
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(p, f, indent=2, ensure_ascii=False)

def log(message):
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{time_str}] {message}\n")

@app.route("/")
def index():
    return render_template("index.html", tasks=tasks, progress=load_progress())

@app.post("/check/<int:task_id>")
def check(task_id):
    code = request.json["code"]
    with open(f"tests/task{task_id}.json", encoding="utf-8") as f:
        test_data = json.load(f)

    progress = load_progress()
    results = []
    all_ok = True

    log(f"=== Проверка задачи {task_id} ===")
    log(f"Получен код:\n{code}")

    for i, input_set in enumerate(test_data["inputs"]):
        try:
            # Формируем один большой input для subprocess
            inp = "\n".join(input_set) + "\n"
            p = subprocess.run(
                ["python", "-c", code],
                input=inp,
                text=True,
                capture_output=True,
                timeout=2
            )
            expected = test_data["outputs"][i].strip()
            got = p.stdout.strip()
            ok = (got == expected)
            if not ok:
                all_ok = False

            results.append({
                "test": i+1,
                "input": input_set,
                "expected": expected,
                "got": got,
                "ok": ok
            })

            log(f"Тест {i+1}: {'OK' if ok else 'FAIL'}")
            log(f"Ввод: {input_set}")
            log(f"Ожидалось: {expected}")
            log(f"Получено: {got}")

        except subprocess.TimeoutExpired:
            all_ok = False
            results.append({"test": i+1, "ok": False, "error": "Time limit"})
            log(f"Тест {i+1}: TIMEOUT")

    old_status = progress.get(str(task_id), "new")
    progress[str(task_id)] = "ok" if all_ok else "fail"
    save_progress(progress)
    log(f"Статус задачи {task_id}: {old_status} -> {progress[str(task_id)]}")
    log(f"=== Конец проверки задачи {task_id} ===\n")

    return jsonify({"results": results, "status": progress[str(task_id)]})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
