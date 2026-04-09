"""Root Python entrypoint fallback for Vercel.
If Vercel forces Python runtime detection, this callable prevents build-time entrypoint errors.
"""


def app(environ, start_response):
    status = "200 OK"
    headers = [("Content-Type", "text/html; charset=utf-8")]
    start_response(status, headers)
    body = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta http-equiv='refresh' content='0; url=/index.html'>"
        "<title>On-Top</title></head><body>"
        "<p>Redirecting to On-Top gateway...</p>"
        "</body></html>"
    )
    return [body.encode("utf-8")]
