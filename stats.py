from datetime import date

def build_stats(tasks):

    total = len(tasks)

    total_done = 0
    total_progress = 0
    total_todo = 0
    total_overdue = 0
    today = date.today()

    for task in tasks:
        if task.status == "done":
            total_done += 1
        elif task.status == "inprogress":
            total_progress += 1
        else:
            total_todo += 1
        
        if task.due_date and task.due_date < today and task.status != "done":
            total_overdue += 1

    if total > 0:
        completion = (total_done / total) * 100
    else:
        completion = 0.0

    return {"total": total,
            "status_done": total_done,
            "status_progress": total_progress,
            "status_todo": total_todo,
            "overdue": total_overdue,
            "completion": round(completion, 1)}