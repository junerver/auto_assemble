from webhook.config import PORT, DEBUG
from webhook.webhook_server import create_app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=PORT, ssl_context=None, debug=DEBUG, use_reloader=DEBUG)
