import os

parts = []

for (root, _, files) in os.walk(".", topdown=True):
  if ".git" in root: continue
  for file in files:
    if file == "upload.py": continue
    abs_path = os.path.abspath(root + "\\" + file)
    local_path = ":/" + file
    parts.append(f"cp {abs_path} {local_path}")

cmd = "mpremote connect COM5 " + " + ".join(parts)
os.system(cmd)