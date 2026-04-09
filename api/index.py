"""Vercel Python fallback entrypoint.
이 파일은 Vercel이 Python 런타임을 강제 감지했을 때 엔트리포인트 누락 오류를 방지합니다.
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
