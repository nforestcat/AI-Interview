import subprocess
import os

env = os.environ.copy()
env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'
if 'ComSpec' in env:
    del env['ComSpec']

strict_prompt = "Respond exactly with: {\"test\": 123}"

try:
    p = subprocess.run(
        ["gemini.cmd", "-p", strict_prompt, "-m", "gemini-3.1-pro-preview"],
        capture_output=True,
        text=True,
        encoding='utf-8',
        env=env
    )
    print("STDOUT:", repr(p.stdout))
    print("STDERR:", repr(p.stderr))
except Exception as e:
    print("ERROR:", str(e))
