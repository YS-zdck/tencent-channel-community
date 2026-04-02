import os
import json
from apscheduler.schedulers.background import BackgroundScheduler
from tool_runner import run_tool
from datetime import datetime

scheduler = BackgroundScheduler()

def start_scheduler():
    if not scheduler.running:
        scheduler.start()

def execute_task(script_path: str, params: dict):
    print(f"[{datetime.now()}] 执行定时任务: {script_path}")
    res = run_tool(script_path, params)
    print(f"[{datetime.now()}] 任务结果: {res}")

def add_job(script_path: str, params: dict, interval_minutes: int):
    start_scheduler()
    job_id = f"job_{script_path.split('/')[-1].split('.')[0]}_{datetime.now().timestamp()}"
    scheduler.add_job(
        execute_task,
        "interval",
        minutes=interval_minutes,
        args=[script_path, params],
        id=job_id,
        replace_existing=True
    )
    return job_id

def get_jobs():
    if not scheduler.running:
        return []
    return scheduler.get_jobs()

def remove_job(job_id: str):
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
