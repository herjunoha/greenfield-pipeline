"""manual driver: nothing can observe this step, so it hands the instruction to the owner and observes nothing."""
import json
import sys
import uuid

req = json.load(sys.stdin)
steps = [(s.get("do") or {}).get("manual") or {} for s in req.get("steps") or []]
sys.stdout.write(json.dumps({
    "session_id": uuid.uuid4().hex, "steps": [], "final_state": {}, "manual": True,
    "instructions": [s.get("instruction", "") for s in steps], "error": "manual step, needs the owner"}))
