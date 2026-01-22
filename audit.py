from datetime import datetime

def log_action(username, action):
    with open("audit.log", "a") as f:
        f.write(f"{datetime.now()} | {username} | {action}\n")
