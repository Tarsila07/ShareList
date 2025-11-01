import socket
import threading
import json
import os

tasks = [] 
lock = threading.Lock()
HOST = "0.0.0.0"
PORT = 5050
USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f: json.dump({}, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

users = load_users()

def handle_client(conn, addr):
    print(f"[NOVA CONEXAO] {addr} conectado.") 
    conn.sendall("Bem-vindo à ShareList!\n".encode()) 

    try:
        while True:
            logged_user = None
            
            while not logged_user:
                conn.sendall("Digite LOGIN ou REGISTER: ".encode()) 
                cmd_data = conn.recv(1024).decode().strip().upper()
                if not cmd_data: continue 

                if cmd_data == "LOGIN":
                    conn.sendall("Usuário: ".encode()) 
                    user = conn.recv(1024).decode().strip()
                    if not user: continue 

                    conn.sendall("Senha: ".encode()) 
                    pwd = conn.recv(1024).decode().strip()
                    if not pwd: continue 

                    with lock:
                        if user in users:
                            if users[user] == pwd:
                                logged_user = user
                                conn.sendall(f"Login bem-sucedido! Bem-vindo, {user}.\n".encode())
                                print(f"[{user}] fez login com sucesso.")
                            else:
                                conn.sendall("Senha incorreta.\n".encode())
                        else:
                            conn.sendall("Usuário não registrado.\n".encode())

                elif cmd_data == "REGISTER":
                    conn.sendall("Novo Usuário: ".encode())
                    user = conn.recv(1024).decode().strip()
                    if not user: continue 

                    conn.sendall("Nova Senha: ".encode())
                    pwd = conn.recv(1024).decode().strip()
                    if not pwd: continue 

                    with lock:
                        if user in users:
                            conn.sendall("Usuário já existe.\n".encode())
                        else:
                            users[user] = pwd
                            save_users(users)
                            logged_user = user 
                            conn.sendall(f"Usuário {user} registrado com sucesso!\n".encode())
                            print(f"[{user}] registrou uma nova conta.") 
                else:
                    conn.sendall("Comando inválido. Digite LOGIN ou REGISTER.\n".encode())
            
            while logged_user:
                conn.sendall(f"({logged_user}) >> ".encode())
                data = conn.recv(1024).decode().strip()
                if not data:
                    logged_user = None 
                    break 
                
                cmd_upper = data.upper()
                response = "" 

                if cmd_upper == "SAIR":
                    with lock:
                        response = process_command(data, logged_user)
                    conn.sendall(response.encode())
                    return 

                elif cmd_upper == "DELUSER":
                    with lock:
                        print(f"[{logged_user}] Solicitou a remoção da conta.")
                        if logged_user in users:
                            del users[logged_user]
                            save_users(users)
                            response = " Usuário removido. Voltando à tela de login.\n"
                            print(f"[{logged_user}] Conta removida com sucesso.") 
                        else:
                            response = "ERRO: Não foi possível remover.\n"
                    logged_user = None 

                else:
                    try:
                        with lock:
                            response = process_command(data, logged_user) 
                    except Exception as e:
                        print(f"*** ERRO NO SERVIDOR: {e} ***")
                        response = "ERRO: Ocorreu um erro interno no servidor.\n"
                
                conn.sendall(response.encode())

    except ConnectionResetError:
        print(f"[{addr}] Ligação perdida abruptamente.")
    except Exception as e:
        print(f"[{addr}] Erro de rede: {e}")
    finally:
        conn.close()
        user_log = logged_user if logged_user else str(addr)
        print(f"[DESCONECTADO] [{user_log}]") 

def process_command(msg, user):
    parts = msg.split(" ", 1)
    cmd = parts[0].upper()

    if cmd == "ADD" and len(parts) > 1:
        tarefa_desc = parts[1]
        tasks.append({"desc": tarefa_desc, "done": False})
        print(f"[{user}] Adicionou a tarefa: '{tarefa_desc}'") 
        return "OK Tarefa adicionada\n"

    elif cmd == "LIST":
        print(f"[{user}] Solicitou a lista de tarefas.")
        if not tasks: return "Nenhuma tarefa.\n"
        return "\n".join([f"{i+1} - {'[x]' if t['done'] else '[ ]'} {t['desc']}" for i, t in enumerate(tasks)]) + "\n"

    elif cmd == "DONE" and len(parts) > 1:
        try:
            i = int(parts[1]) - 1
            tarefa_desc = tasks[i]['desc'] 
            tasks[i]["done"] = True
            print(f"[{user}] Concluiu a tarefa: '{tarefa_desc}'") 
            return f"OK Tarefa {i+1} concluída\n"
        except (ValueError, IndexError): 
            print(f"[{user}] Tentou concluir tarefa inválida: {parts[1]}") 
            return "Erro: índice inválido.\n"

    elif cmd == "DEL" and len(parts) > 1:
        try:
            i = int(parts[1]) - 1
            tarefa_removida = tasks.pop(i)
            print(f"[{user}] Removeu a tarefa: '{tarefa_removida['desc']}'") 
            return f"OK Tarefa {i+1} removida\n"
        except (ValueError, IndexError): 
            print(f"[{user}] Tentou remover tarefa inválida: {parts[1]}") 
            return "Erro: índice inválido.\n"
    
    elif cmd == "SAIR": 
        print(f"[{user}] Fez logout.")
        return "Até logo!\n" 

    print(f"[{user}] Enviou comando desconhecido: '{msg}'") 
    return "Comando desconhecido.\n" 

def start():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.settimeout(1.0)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVIDOR] Rodando em {HOST}: {PORT}")
    try:
        while True:
            try:
                conn, addr = server.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr))
                thread.start()
            except socket.timeout: pass 
    except KeyboardInterrupt:
        print("\n[DESLIGANDO] Recebido Cancelamento. A desligar...") #quando vc aperta ctrl C
    finally:
        server.close()
        print("[SERVIDOR DESLIGADO]")

if __name__ == "__main__":
    start()