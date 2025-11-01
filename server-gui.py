# servidor.py (Versão 4.1 - Com JSON)

import socket
import threading
import json
import os
import random
import string

# Define o host e a porta em que o servidor vai escutar conexões
HOST = "0.0.0.0"
PORT = 5050

# Define os nomes dos arquivos que armazenam usuários e listas
USERS_FILE = "users.json"
LISTAS_FILE = "listas.json"

# Cria um lock para evitar condições de corrida em operações de I/O
lock = threading.Lock()

# Função para carregar dados de um arquivo JSON
def load_data(filepath):
    with lock:
        if not os.path.exists(filepath):
            # Cria o arquivo se ele não existir
            with open(filepath, "w") as f:
                json.dump({}, f)
            return {}
        try:
            # Lê o arquivo e retorna o conteúdo em formato de dicionário
            with open(filepath, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            # Recria o arquivo em caso de erro de leitura JSON
            with open(filepath, "w") as f:
                json.dump({}, f)
            return {}

# Função para salvar dados em um arquivo JSON
def save_data(filepath, data):
    with lock:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)

# Gera um código aleatório para identificar listas
def generate_code(length=4):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# Processa os comandos relacionados às listas (ADD, DONE, UNDONE, DEL, LIST)
def process_list_command(msg, list_code, user):
    listas = load_data(LISTAS_FILE)
    if list_code not in listas:
        return "LIST_ERR Lista inexistente.\n"
    tasks = listas[list_code]["tarefas"]
    parts = msg.split(" ", 1)
    cmd = parts[0].upper()
    response = "LIST_ERR Comando inválido.\n"
    if cmd == "LIST":
        # Retorna todas as tarefas da lista
        response = f"LIST_R {json.dumps(tasks)}\n"
    elif cmd == "ADD" and len(parts) > 1:
        # Adiciona uma nova tarefa
        desc = parts[1]
        tasks.append({"desc": desc, "done": False})
        save_data(LISTAS_FILE, listas)
        response = f"LIST_R {json.dumps(tasks)}\n"
    elif cmd in ("DONE", "UNDONE") and len(parts) > 1:
        # Marca ou desmarca uma tarefa como concluída
        try:
            idx = int(parts[1]) - 1
            tasks[idx]["done"] = (cmd == "DONE")
            save_data(LISTAS_FILE, listas)
            response = f"LIST_R {json.dumps(tasks)}\n"
        except (ValueError, IndexError):
            response = "LIST_ERR Índice inválido.\n"
    elif cmd == "DEL" and len(parts) > 1:
        # Remove uma tarefa da lista
        try:
            idx = int(parts[1]) - 1
            tasks.pop(idx)
            save_data(LISTAS_FILE, listas)
            response = f"LIST_R {json.dumps(tasks)}\n"
        except (ValueError, IndexError):
            response = "LIST_ERR Índice inválido.\n"
    return response

# Função que lida com cada cliente conectado
def handle_client(conn, addr):
    print(f"[NOVA CONEXÃO] {addr}")
    conn.sendall("Bem-vindo à ShareList v4.1!\n".encode())
    logged_user = None

    try:
        buffer = ""
        # Loop de autenticação até o usuário logar
        while not logged_user:
            data = conn.recv(1024)
            if not data:
                continue
            buffer += data.decode()
            if "\n" not in buffer and len(buffer.split()) < 3:
                continue
            msg = buffer.strip()
            buffer = ""
            parts = msg.split(" ")
            cmd = parts[0].upper()
            if cmd == "LOGIN" and len(parts) >= 3:
                # Realiza login do usuário
                user, pwd = parts[1], parts[2]
                users = load_data(USERS_FILE)
                if user not in users:
                    conn.sendall("LOGIN_NOUSER\n".encode())
                elif users[user]["password"] != pwd:
                    conn.sendall("LOGIN_WRONGPASS\n".encode())
                else:
                    logged_user = user
                    conn.sendall(f"LOGIN_OK {user}\n".encode())
                    print(f"{user} logado com sucesso.")
            elif cmd == "REGISTER" and len(parts) >= 3:
                # Registra um novo usuário
                user, pwd = parts[1], parts[2]
                users = load_data(USERS_FILE)
                if user in users:
                    conn.sendall("REGISTER_FAIL\n".encode())
                else:
                    users[user] = {"password": pwd, "listas_acessiveis": []}
                    save_data(USERS_FILE, users)
                    conn.sendall("REGISTER_OK\n".encode())
                    print(f"Novo usuário registrado: {user}")

        # Loop principal do usuário logado
        while True:
            data = conn.recv(1024)
            if not data:
                break
            msg = data.decode().strip()
            parts = msg.split(" ", 1)
            cmd = parts[0].upper()
            if cmd == "VER":
                # Lista as listas acessíveis do usuário
                users = load_data(USERS_FILE)
                listas = load_data(LISTAS_FILE)
                codes = users[logged_user]["listas_acessiveis"]
                if not codes:
                    conn.sendall("VER_R Nenhuma lista encontrada.\n".encode())
                else:
                    resposta = "VER_R Suas Listas:\n"
                    for i, c in enumerate(codes, 1):
                        titulo = listas.get(c, {}).get("titulo", "(Apagada)")
                        resposta += f"{i}. {titulo} (Código: {c})\n"
                    conn.sendall(resposta.encode())
            elif cmd == "CRIAR" and len(parts) > 1:
                # Cria uma nova lista e gera código de acesso
                titulo = parts[1]
                users = load_data(USERS_FILE)
                listas = load_data(LISTAS_FILE)
                code = generate_code()
                while code in listas:
                    code = generate_code()
                listas[code] = {"titulo": titulo, "tarefas": []}
                users[logged_user]["listas_acessiveis"].append(code)
                save_data(USERS_FILE, users)
                save_data(LISTAS_FILE, listas)
                conn.sendall(f"CRIAR_R Lista '{titulo}' criada! Código: {code}\n".encode())
            elif cmd == "ENTRAR" and len(parts) > 1:
                # Permite o usuário entrar em uma lista existente
                code = parts[1].upper()
                listas = load_data(LISTAS_FILE)
                users = load_data(USERS_FILE)
                if code not in listas:
                    conn.sendall("ENTRAR_R Código inválido.\n".encode())
                else:
                    conn.sendall(f"MODO_LISTA {listas[code]['titulo']}\n".encode())
                    while True:
                        msg = conn.recv(1024)
                        if not msg:
                            break
                        msg = msg.decode().strip()
                        if msg.upper() == "VOLTAR":
                            conn.sendall("MODO_LOBBY Voltando...\n".encode())
                            break
                        # Processa comandos da lista enquanto o usuário estiver dentro dela
                        response = process_list_command(msg, code, logged_user)
                        conn.sendall(response.encode())
            elif cmd == "SAIR":
                # Finaliza a conexão com o cliente
                conn.sendall("Até logo!\n".encode())
                break
    except (ConnectionResetError, socket.error):
        print(f"[DESCONECTADO] {addr}")
    finally:
        conn.close()

# Função principal que inicia o servidor
def start():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVIDOR] Rodando em {HOST}:{PORT}")
    try:
        # Aceita novas conexões continuamente
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\nEncerrando servidor...")
    finally:
        server.close()

# Ponto de entrada do programa
if __name__ == "__main__":
    start()
