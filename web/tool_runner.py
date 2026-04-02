import subprocess
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.resolve()

def run_tool(script_rel_path: str, params: dict) -> dict:
    script_path = BASE_DIR / script_rel_path
    if not script_path.exists():
        return {"code": -1, "msg": f"Script not found: {script_path}", "data": None}
        
    env = os.environ.copy()
    env["QQ_AI_CONNECT_DOTENV"] = str(BASE_DIR / ".env")
    
    try:
        proc = subprocess.run(
            ["python3", str(script_path)],
            input=json.dumps(params),
            capture_output=True,
            text=True,
            env=env
        )
    except Exception as e:
        return {"code": -1, "msg": str(e), "data": None}
        
    if proc.returncode != 0:
        try:
            return json.loads(proc.stderr)
        except:
            return {"code": proc.returncode, "msg": proc.stderr or proc.stdout, "data": None}
            
    try:
        return json.loads(proc.stdout)
    except Exception as e:
        return {"code": -1, "msg": f"Failed to parse JSON: {proc.stdout}", "data": None}
