#!/usr/bin/env python3
"""
Вебзастосунок з HTTP сервером та Socket сервером для роботи з MongoDB
"""

import json
import logging
import mimetypes
import multiprocessing
import signal
import socket
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, Any, Optional

import pymongo
from pymongo.collection import Collection
from pymongo.database import Database

# Імпорт конфігурації
from config import get_config

# Ініціалізація конфігурації
config = get_config()

# Налаштування логування на основі конфігурації
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Валідація конфігурації при запуску
if not config.validate():
    logger.error("Configuration validation failed!")
    sys.exit(1)

logger.info(f"Starting application with {config.__class__.__name__}")


class HTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP сервер для обробки запитів"""

    def _set_headers(self, content_type: str = "text/html", status: int = 200) -> None:
        """Встановлення заголовків відповіді"""
        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.end_headers()

    def _get_static_file(self, file_path: Path) -> Optional[bytes]:
        """Читання статичного файлу"""
        try:
            if file_path.exists() and file_path.is_file():
                return file_path.read_bytes()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
        return None

    def _send_file(self, file_path: Path) -> None:
        """Відправка файлу клієнту"""
        content = self._get_static_file(file_path)
        if content:
            content_type, _ = mimetypes.guess_type(str(file_path))
            if not content_type:
                content_type = "text/plain"
            self._set_headers(content_type)
            self.wfile.write(content)
        else:
            self._send_error_page()

    def _send_error_page(self) -> None:
        """Відправка сторінки помилки 404"""
        error_file = config.FRONT_DIR / "error.html"
        content = self._get_static_file(error_file)
        if content:
            self._set_headers("text/html", 404)
            self.wfile.write(content)
        else:
            self._set_headers("text/html", 404)
            self.wfile.write(b"<h1>404 Not Found</h1>")

    def _send_message_to_socket(self, data: Dict[str, Any]) -> bool:
        """Відправка даних на Socket сервер"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((config.SOCKET_HOST, config.SOCKET_PORT))
                message = json.dumps(data).encode('utf-8')
                sock.send(message)
                return True
        except Exception as e:
            logger.error(f"Error sending to socket server: {e}")
            return False

    def do_GET(self) -> None:
        """Обробка GET запитів"""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/" or path == "/index.html":
            file_path = config.FRONT_DIR / "index.html"
        elif path == "/message.html":
            file_path = config.FRONT_DIR / "message.html"
        elif path == "/style.css":
            file_path = config.FRONT_DIR / "style.css"
        elif path == "/logo.png":
            file_path = config.FRONT_DIR / "logo.png"
        else:
            self._send_error_page()
            return

        self._send_file(file_path)

    def do_POST(self) -> None:
        """Обробка POST запитів"""
        if self.path == "/message":
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length).decode('utf-8')
                data = urllib.parse.parse_qs(post_data)
                
                # Отримання даних з форми
                username = data.get('username', [''])[0]
                message = data.get('message', [''])[0]
                
                if username and message:
                    # Підготовка даних для відправки
                    socket_data = {
                        'username': username,
                        'message': message
                    }
                    
                    # Відправка на Socket сервер
                    if self._send_message_to_socket(socket_data):
                        # Перенаправлення на головну сторінку після успішної відправки
                        self.send_response(302)
                        self.send_header('Location', '/')
                        self.end_headers()
                    else:
                        self._send_error_page()
                else:
                    self._send_error_page()
                    
            except Exception as e:
                logger.error(f"Error processing POST request: {e}")
                self._send_error_page()
        else:
            self._send_error_page()

    def log_message(self, format: str, *args: Any) -> None:
        """Кастомне логування"""
        logger.info(f"{self.client_address[0]} - {format % args}")


class SocketServer:
    """Socket сервер для обробки повідомлень та збереження в MongoDB"""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.mongo_client: Optional[pymongo.MongoClient] = None
        self.db: Optional[Database] = None
        self.collection: Optional[Collection] = None
        self.server_socket: Optional[socket.socket] = None
        self.executor: Optional[ThreadPoolExecutor] = None
        self.is_running = False

    def _connect_to_mongo(self) -> bool:
        """Підключення до MongoDB з connection pooling"""
        try:
            self.mongo_client = pymongo.MongoClient(
                config.MONGO_URI, 
                maxPoolSize=config.MONGO_MAX_POOL_SIZE,
                minPoolSize=config.MONGO_MIN_POOL_SIZE,
                maxIdleTimeMS=config.MONGO_MAX_IDLE_TIME_MS,
                waitQueueTimeoutMS=config.MONGO_WAIT_QUEUE_TIMEOUT_MS
            )
            self.db = self.mongo_client[config.DB_NAME]
            self.collection = self.db[config.COLLECTION_NAME]
            # Тест підключення
            self.mongo_client.admin.command('ping')
            logger.info("Connected to MongoDB with connection pooling")
            return True
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            return False

    def _save_message(self, data: Dict[str, Any]) -> bool:
        """Збереження повідомлення в MongoDB"""
        try:
            if self.collection is None:
                logger.error("MongoDB collection is not initialized")
                return False
                
            document = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                "username": data.get("username", ""),
                "message": data.get("message", "")
            }
            self.collection.insert_one(document)
            logger.info(f"Message saved: {document}")
            return True
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return False

    def shutdown_handler(self, signum: int, frame) -> None:
        """Обробник сигналів для елегантного закриття"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.is_running = False
        
        # Закриття server socket для припинення accept()
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                logger.error(f"Error closing server socket: {e}")
        
        # Закриття ThreadPoolExecutor
        if self.executor:
            logger.info("Shutting down thread pool...")
            self.executor.shutdown(wait=True)
        
        # Закриття MongoDB з'єднання
        if self.mongo_client:
            try:
                self.mongo_client.close()
                logger.info("MongoDB connection closed")
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {e}")

    def _handle_client(self, client_socket: socket.socket, address: tuple) -> None:
        """Обробка клієнтського підключення"""
        try:
            # Встановлення timeout для socket операцій
            client_socket.settimeout(30.0)
            
            data = client_socket.recv(1024).decode('utf-8')
            if data:
                message_data = json.loads(data)
                self._save_message(message_data)
                logger.info(f"Processed message from {address}")
            else:
                logger.warning(f"Empty data received from {address}")
        except socket.timeout:
            logger.warning(f"Timeout handling client {address}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from {address}: {e}")
        except Exception as e:
            logger.error(f"Error handling client {address}: {e}")
        finally:
            try:
                client_socket.close()
            except Exception as e:
                logger.error(f"Error closing client socket {address}: {e}")

    def start(self) -> None:
        """Запуск Socket сервера з ThreadPoolExecutor"""
        if not self._connect_to_mongo():
            logger.error("Failed to connect to MongoDB")
            return

        # Налаштування обробників сигналів
        signal.signal(signal.SIGTERM, self.shutdown_handler)
        signal.signal(signal.SIGINT, self.shutdown_handler)

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)  # Збільшений backlog
            
            logger.info(f"Socket server started on {self.host}:{self.port}")
            self.is_running = True
            
            # Використання ThreadPoolExecutor для обробки клієнтів
            with ThreadPoolExecutor(max_workers=config.THREAD_POOL_MAX_WORKERS, 
                                  thread_name_prefix="SocketWorker") as executor:
                self.executor = executor
                
                while self.is_running:
                    try:
                        client_socket, address = self.server_socket.accept()
                        if self.is_running:  # Перевірка після accept
                            executor.submit(self._handle_client, client_socket, address)
                    except OSError as e:
                        if self.is_running:  # Логувати помилку тільки якщо сервер ще працює
                            logger.error(f"Socket accept error: {e}")
                        break
                    except Exception as e:
                        logger.error(f"Unexpected error in server loop: {e}")
                        if self.is_running:
                            continue
                        else:
                            break
                            
        except Exception as e:
            logger.error(f"Socket server error: {e}")
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        """Очищення ресурсів при завершенні роботи"""
        logger.info("Cleaning up resources...")
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                logger.error(f"Error closing server socket: {e}")
        
        if self.mongo_client:
            try:
                self.mongo_client.close()
                logger.info("MongoDB connection closed during cleanup")
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {e}")


def start_http_server() -> None:
    """Запуск HTTP сервера з покращеною обробкою сигналів"""
    server = None
    
    def signal_handler(signum, frame):
        logger.info("HTTP server received shutdown signal")
        if server:
            server.shutdown()
    
    # Налаштування обробників сигналів
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        server = HTTPServer((config.HTTP_HOST, config.HTTP_PORT), HTTPRequestHandler)
        logger.info(f"HTTP server started on {config.HTTP_HOST}:{config.HTTP_PORT}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"HTTP server error: {e}")
    finally:
        if server:
            server.server_close()


def start_socket_server() -> None:
    """Запуск Socket сервера з покращеною обробкою сигналів"""
    socket_server = SocketServer(config.SOCKET_HOST, config.SOCKET_PORT)
    
    def signal_handler(signum, frame):
        logger.info("Socket server received shutdown signal")
        socket_server.shutdown_handler(signum, frame)
    
    # Налаштування обробників сигналів для процесу
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    socket_server.start()


def main() -> None:
    """Головна функція"""
    logger.info("Starting application...")
    
    # Створення процесів для HTTP та Socket серверів
    http_process = multiprocessing.Process(target=start_http_server)
    socket_process = multiprocessing.Process(target=start_socket_server)
    
    try:
        http_process.start()
        socket_process.start()
        
        http_process.join()
        socket_process.join()
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        http_process.terminate()
        socket_process.terminate()
        http_process.join()
        socket_process.join()


if __name__ == "__main__":
    main()
