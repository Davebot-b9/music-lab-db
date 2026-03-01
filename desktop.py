import webview
import threading
import uvicorn
from main import app

def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == '__main__':
    # Arrancar FastAPI en un hilo en segundo plano
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    
    # Crear y abrir la ventana nativa de escritorio
    webview.create_window('Music Place Dashboard', 'http://127.0.0.1:8000')
    webview.start()
