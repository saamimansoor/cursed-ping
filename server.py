from flask import Flask
import subprocess
import os

# Install Chromium on startup
os.system("playwright install chromium")

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Cursed Ping is alive!"

@app.route("/run-bot")
def run_bot():
    try:
        subprocess.run(["python", "visitcb.py"], check=True)
        return "✅ Ping Successful!"
    except Exception as e:
        return f"❌ Bot run failed: {e}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)