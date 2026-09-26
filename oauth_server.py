from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

import threading


class OAuthCallbackServer:

    def __init__(
        self,
        port=8080
    ):

        self.port = port

        self.server = None

        self.thread = None

        self.callback = None

    def start(
        self,
        callback
    ):

        self.callback = callback

        outer = self

        class Handler(
            BaseHTTPRequestHandler
        ):

            def do_GET(self):

                parsed = urlparse(
                    self.path
                )

                if parsed.path != "/oauth/callback":

                    self.send_response(
                        404
                    )

                    self.end_headers()

                    return

                params = parse_qs(
                    parsed.query
                )

                code = params.get(
                    "code",
                    [None]
                )[0]

                error = params.get(
                    "error",
                    [None]
                )[0]

                error_description = params.get(
                    "error_description",
                    [None]
                )[0]

                if code:

                    html = """
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <title>Facebook Login</title>
                    </head>
                    <body>
                        <h2>Đăng nhập Facebook thành công.</h2>
                        <p>Bạn có thể đóng cửa sổ này.</p>

                        <script>
                            setTimeout(function () {
                                window.close();
                            }, 1500);
                        </script>
                    </body>
                    </html>
                    """

                else:

                    html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <title>Facebook Login Error</title>
                    </head>
                    <body>
                        <h2>Đăng nhập Facebook thất bại.</h2>
                        <p>{error or "Unknown error"}</p>
                        <p>{error_description or ""}</p>
                    </body>
                    </html>
                    """

                body = html.encode(
                    "utf-8"
                )

                self.send_response(
                    200
                )

                self.send_header(
                    "Content-Type",
                    "text/html; charset=utf-8"
                )

                self.send_header(
                    "Content-Length",
                    str(len(body))
                )

                self.end_headers()

                self.wfile.write(
                    body
                )

                if outer.callback:

                    outer.callback(
                        code,
                        error,
                        error_description
                    )

            def log_message(
                self,
                format,
                *args
            ):

                return

        self.server = HTTPServer(
            (
                "127.0.0.1",
                self.port
            ),
            Handler
        )

        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True
        )

        self.thread.start()

    def stop(self):

        if self.server:

            self.server.shutdown()

            self.server.server_close()

            self.server = None