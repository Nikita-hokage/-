import socket
import os

PORT = 9001
BUFSIZE = 4096

def send_file(sock, filename):
    if not os.path.exists(filename):
        print("Файл не найден.")
        return
    sock.sendall(os.path.basename(filename).encode().ljust(256, b'\0'))
    filesize = os.path.getsize(filename)
    sock.sendall(str(filesize).encode().ljust(32, b'\0'))
    with open(filename, 'rb') as f:
        while True:
            data = f.read(BUFSIZE)
            if not data:
                break
            sock.sendall(data)
    print(f"Файл {filename} отправлен.")
    sock.shutdown(socket.SHUT_WR)

def receive_file(sock):
    filename = sock.recv(256).decode().strip('\0')
    filesize = int(sock.recv(32).decode().strip('\0'))
    outfilename = "recv_" + filename
    with open(outfilename, 'wb') as f:
        received = 0
        while received < filesize:
            data = sock.recv(min(BUFSIZE, filesize - received))
            if not data:
                break
            f.write(data)
            received += len(data)
    print(f"Файл {filename} получен как {outfilename}")

def server_mode():
    s = socket.socket()
    s.bind(('0.0.0.0', PORT))
    s.listen(5)
    print(f"Сервер запущен на порту {PORT}")
    while True:
        conn, addr = s.accept()
        print(f"Соединение от {addr}")
        cmd = conn.recv(4).decode()
        if cmd == "SEND":
            receive_file(conn)
        elif cmd == "GETF":
            filename = conn.recv(256).decode().strip('\0')
            send_file(conn, filename)
        conn.close()

def client_mode():
    s = socket.socket()
    host = input("Введите адрес сервера (например, 127.0.0.1): ").strip()
    s.connect((host, PORT))
    mode = input("Выберите действие: отправить файл (s) или получить файл (g): ").strip().lower()
    if mode == 's':
        s.sendall(b"SEND")
        filename = input("Имя файла для отправки: ").strip()
        send_file(s, filename)
    elif mode == 'g':
        s.sendall(b"GETF")
        filename = input("Имя файла для получения: ").strip()
        s.sendall(filename.encode().ljust(256, b'\0'))
        receive_file(s)
    else:
        print("Неизвестная команда")
    s.close()

if __name__ == "__main__":
    role = input("Выберите режим: сервер (s) или клиент (c): ").strip().lower()
    if role == 's':
        server_mode()
    elif role == 'c':
        client_mode()
    else:
        print("Неизвестный режим")
