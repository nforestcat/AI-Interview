import subprocess
import os
import tempfile

env = os.environ.copy()
env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'
if 'ComSpec' in env:
    del env['ComSpec']

strict_prompt = "Respond exactly with: {\"test\": 123}"

with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
    f.write(strict_prompt)
    temp_path = f.name

try:
    cmd = f"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-Content -Raw '{temp_path}' | gemini -p ' ' -m 'gemini-3.1-pro-preview'"
    p = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", cmd],
        capture_output=True,
        text=True,
        encoding='utf-8',
        env=env
    )
    print("STDOUT:", repr(p.stdout))
    print("STDERR:", repr(p.stderr))
finally:
    os.remove(temp_path)
