import socket
import eel

APP_TITLE = "Willow"


def pick_port(preferred=8001):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        if s.connect_ex(("127.0.0.1", preferred)) != 0:
            return preferred

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


eel.init("web")


@eel.expose
def hello():
    return "Connected to Python."


@eel.expose
def listen():
    # TODO: replace with real speech-to-text
    return "---"


MIC_MUTED = True


@eel.expose
def set_mute(is_live: bool):
    global MIC_MUTED
    MIC_MUTED = not is_live
    print("Mic muted:", MIC_MUTED)


def start():
    port = pick_port(8001)
    size = (980, 720)

    eel.start("index.html", size=size, port=port, block=True)


if __name__ == "__main__":
    start()
