"""Docker Engine + Traefik API clients."""
import http.client
import json
import socket

class UnixSocketHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path):
        super().__init__("localhost")
        self.socket_path = socket_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)

def get_docker_api(path):
    try:
        conn = UnixSocketHTTPConnection("/var/run/docker.sock")
        conn.request("GET", path)
        resp = conn.getresponse()
        return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return []

def get_traefik_api():
    for host in ["gateway_gateway", "gateway"]:
        try:
            req = http.client.HTTPConnection(host, 8080, timeout=3)
            req.request("GET", "/api/rawdata")
            resp = req.getresponse()
            data = json.loads(resp.read().decode('utf-8'))
            req.close()
            return data
        except Exception:
            continue
    return {}
