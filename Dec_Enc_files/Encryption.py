import os
import socket
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import scrypt
from Crypto.Random import get_random_bytes

PORT = 9001
BUFSIZE = 4096

def encrypt_file(input_file, output_file, password):
    # Генерируем соль (16 байт) и IV (12 байт)
    salt = get_random_bytes(16)
    iv = get_random_bytes(12)
    # Получаем ключ из пароля и соли (32 байта = 256 бит)
    key = scrypt(password.encode(), salt, 32, N=2 ** 14, r=8, p=1)
    # Читаем исходный файл
    with open(input_file, 'rb') as f:
        data = f.read()
    # Создаём объект шифра AES-GCM
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    # Сохраняем: [IV][salt][ciphertext][tag]
    with open(output_file, 'wb') as f:
        f.write(iv)
        f.write(salt)
        f.write(ciphertext)
        f.write(tag)
    print("Файл зашифрован.")


def decrypt_file(input_file, output_file, password):
    with open(input_file, 'rb') as f:
        iv = f.read(12)
        salt = f.read(16)
        filedata = f.read()
    ciphertext = filedata[:-16]
    tag = filedata[-16:]
    key = scrypt(password.encode(), salt, 32, N=2 ** 14, r=8, p=1)
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    try:
        data = cipher.decrypt_and_verify(ciphertext, tag)
        with open(output_file, 'wb') as f:
            f.write(data)
        print("Файл расшифрован.")
    except Exception as e:
        print("Ошибка расшифровки:", e)

def send_file(sock, filename, password):
    if not os.path.exists(filename):
        print("Файл не найден.")
        return
    encfile = filename + ".enc"
    encrypt_file(filename, encfile, password)
    sock.sendall(os.path.basename(filename).encode().ljust(256, b'\0'))
    filesize = os.path.getsize(encfile)
    sock.sendall(str(filesize).encode().ljust(32, b'\0'))
    with open(encfile, 'rb') as f:
        while True:
            data = f.read(BUFSIZE)
            if not data:
                break
            sock.sendall(data)
    os.remove(encfile)
    print(f"Файл {filename} зашифрован и отправлен.")

def receive_file(sock, password):
    filename = sock.recv(256).decode().strip('\0')
    filesize = int(sock.recv(32).decode().strip('\0'))
    encfile = "recv_" + filename + ".enc"
    with open(encfile, 'wb') as f:
        received = 0
        while received < filesize:
            data = sock.recv(min(BUFSIZE, filesize - received))
            if not data:
                break
            f.write(data)
            received += len(data)
    print(f"Зашифрованный файл {encfile} получен.")
    outfilename = "recv_" + filename
    if decrypt_file(encfile, outfilename, password):
        print(f"Файл {outfilename} расшифрован и сохранён.")
        os.remove(encfile)
    else:
        print("Не удалось расшифровать файл.")

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
            password = input("Введите пароль для расшифровки получаемого файла: ")
            receive_file(conn, password)
        elif cmd == "GETF":
            filename = conn.recv(256).decode().strip('\0')
            password = input(f"Введите пароль для шифрования файла {filename}: ")
            send_file(conn, filename, password)
        conn.close()

def client_mode():
    s = socket.socket()
    host = input("Введите адрес сервера (например, 127.0.0.1): ").strip()
    s.connect((host, PORT))
    mode = input("Выберите действие: отправить файл (s) или получить файл (g): ").strip().lower()
    if mode == 's':
        s.sendall(b"SEND")
        filename = input("Имя файла для отправки: ").strip()
        password = input("Пароль для шифрования: ")
        send_file(s, filename, password)
    elif mode == 'g':
        s.sendall(b"GETF")
        filename = input("Имя файла для получения: ").strip()
        s.sendall(filename.encode().ljust(256, b'\0'))
        password = input("Пароль для расшифровки: ")
        receive_file(s, password)
    else:
        print("Неизвестная команда")
    s.close()


if __name__ == "__main__":
    operation = input('Выберете режим работы (t = передача файла, k = шифрование файла на хосте): ').strip().lower()
    if operation == 't':
        role = input("Выберите режим: сервер (s) или клиент (c): ").strip().lower()
        if role == 's':
            server_mode()
        elif role == 'c':
            client_mode()
        else:
            print("Неизвестный режим")
    elif operation == 'k':
        while True:
            mode = input("Выберите режим (e=шифрование, d=дешифрование, stop = закончить работу): ").strip().lower()
            if mode != 'e' and mode != 'd' and mode != 'stop':
                print('Неизвестный режим')
                continue
            elif mode == 'stop':
                break
            infile = input("Имя входного файла: ").strip()
            if os.path.exists(infile):
                outfile = input("Имя выходного файла: ").strip()
                password = input("Пароль: ").strip()
                if mode == 'e':
                    encrypt_file(infile, outfile, password)
                elif mode == 'd':
                    decrypt_file(infile, outfile, password)
            else:
                print('Неизвестный файл')
