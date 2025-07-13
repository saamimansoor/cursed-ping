from flask import Flask
from visitcb import run, parse_args

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Cursed Ping is alive!"

@app.route("/run-bot")
def run_bot():
    try:
        opts = parse_args()
        run(opts.future_min, opts.lookback_hrs)
        return "✅ Bot executed!"
    except Exception as e:
        return f"❌ Bot run failed: {e}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)