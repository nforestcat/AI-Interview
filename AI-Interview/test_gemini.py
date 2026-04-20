import subprocess
import os

env = os.environ.copy()
env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'

prompt = "Respond with EXACTLY: {'test': '한국어'}"
cmd = ["gemini.cmd", "-p", " ", "-m", "gemini-3.1-pro-preview"]

p = subprocess.run(
    cmd,
    input=prompt,
    capture_output=True,
    text=True,
    encoding='utf-8',
    env=env
)

print('STDOUT:', repr(p.stdout))
print('STDERR:', repr(p.stderr))
