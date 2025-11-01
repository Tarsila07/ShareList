# servidor.py (Versão 4.0 - Com JSON)
import socket
import threading
import json
import os
import random
import string

#SERVER PARA A INTERFACE GRAFICA

# --- Configurações Globais ---
HOST = "0.0.0.0"
PORT = 5050
USERS_FILE = "users.json"
LISTAS_FILE = "listas.json"
lock = threading.Lock() 

# --- Funções de Base de Dados (Sem Alterações) ---
def load_data(filepath):
    with lock:
        if not os.path.exists(filepath):
            with open(filepath, "w") as f: json.dump({}, f)
            return {}
        try:
            with open(filepath, "r") as f: return json.load(f)
        except json.JSONDecodeError:
            with open(filepath, "w") as f: json.dump({}, f)
            return {}

def save_data(filepath, data):
    with lock:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)

def generate_code(length=4):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# --- LÓGICA DE COMANDOS (MUDANÇA PRINCIPAL AQUI) ---
def process_list_command(msg, list_code, user):
    """
    Processa comandos ADD, LIST, DONE, DEL.
    AGORA RESPONDE COM JSON (LIST_R) para a GUI.
    """
    
    listas = load_data(LISTAS_FILE) 
    
    if list_code not in listas:
        return "LIST_ERR A lista foi apagada.\n"
    
    current_tasks = listas[list_code]["tarefas"]
    
    parts = msg.split(" ", 1)
    cmd = parts[0].upper()
    response = "LIST_ERR Comando desconhecido.\n" # Resposta de erro

    # Comando LIST: Apenas retorna a lista em JSON
    if cmd == "LIST":
        print(f"ℹ️ [{user}] Solicitou a lista '{list_code}' (JSON)")
        response = f"LIST_R {json.dumps(current_tasks)}\n"

    # Comando ADD: Adiciona e retorna a nova lista
    elif cmd == "ADD" and len(parts) > 1:
        tarefa_desc = parts[1]
        current_tasks.append({"desc": tarefa_desc, "done": False})
        save_data(LISTAS_FILE, listas) # Salva
        print(f"✅ [{user}] Adicionou '{tarefa_desc}' à lista '{list_code}'")
        response = f"LIST_R {json.dumps(current_tasks)}\n"
        
    # Comando DONE: Marca/desmarca (toggle) e retorna a nova lista
    elif cmd == "DONE" and len(parts) > 1:
        try:
            i = int(parts[1]) - 1
            # MUDANÇA: Agora faz um "toggle" (inverte o estado)
            current_tasks[i]["done"] = not current_tasks[i]["done"]
            save_data(LISTAS_FILE, listas) # Salva
            print(f"👍 [{user}] Alterou o estado de '{current_tasks[i]['desc']}'")
            response = f"LIST_R {json.dumps(current_tasks)}\n"
        except (ValueError, IndexError): 
            response = "LIST_ERR Índice inválido.\n"

    # Comando DEL: Deleta e retorna a nova lista
    elif cmd == "DEL" and len(parts) > 1:
        try:
            i = int(parts[1]) - 1
            tarefa_removida = current_tasks.pop(i)
            save_data(LISTAS_FILE, listas) # Salva
            print(f"❌ [{user}] Removeu '{tarefa_removida['desc']}'")
            response = f"LIST_R {json.dumps(current_tasks)}\n"
        except (ValueError, IndexError): 
            response = "LIST_ERR Índice inválido.\n"
    
    return response

# --- Lógica Principal do Cliente (handle_client) (Sem Alterações) ---
def handle_client(conn, addr):
    print(f"[NOVA CONEXAO] {addr} conectado.")
    conn.sendall("Bem-vindo à ShareList v4.0 (JSON-GUI)!\n".encode()) 
    logged_user = None

    try:
        # --- ESTADO 1: LOOP DE LOGIN ---
        while not logged_user:
            data = conn.recv(1024).decode().strip()
            if not data: return 

            parts = data.split(" ")
            cmd = parts[0].upper()
            
            if cmd == "LOGIN" and len(parts) == 3:
                user = parts[1]
                pwd = parts[2]
                
                users = load_data(USERS_FILE)
                if user in users and users[user]["password"] == pwd:
                    logged_user = user
                    conn.sendall(f"LOGIN_OK {user}\n".encode())
                    print(f"🔒 [{user}] fez login com sucesso.")
                else:
                    conn.sendall("AUTH_FAIL Usuário ou senha incorretos.\n".encode())

            elif cmd == "REGISTER" and len(parts) == 3:
                user = parts[1]
                pwd = parts[2]

                users = load_data(USERS_FILE)
                if user in users:
                    conn.sendall("AUTH_FAIL Usuário já existe.\n".encode())
                else:
                    users[user] = {"password": pwd, "listas_acessiveis": []}
                    save_data(USERS_FILE, users)
                    logged_user = user 
                    conn.sendall(f"LOGIN_OK {user}\n".encode())
                    print(f"📝 [{user}] registrou uma nova conta.")
            else:
                conn.sendall("AUTH_FAIL Comando inválido.\n".encode())
        
        # --- ESTADO 2: LOOP DO LOBBY ---
        while True: 
            data = conn.recv(1024).decode().strip()
            if not data: break

            parts = data.split(" ", 1)
            cmd_lobby = parts[0].upper()
            
            if cmd_lobby == "VER":
                users = load_data(USERS_FILE)
                listas = load_data(LISTAS_FILE)
                user_list_codes = users[logged_user]["listas_acessiveis"]
                if not user_list_codes:
                    conn.sendall("VER_R Nenhuma lista encontrada.\n".encode())
                    continue
                
                resposta = "VER_R Suas Listas:\n"
                for i, code in enumerate(user_list_codes, 1):
                    titulo = listas.get(code, {}).get("titulo", f"Lista {code} (Apagada)")
                    resposta += f" {i}. {titulo} (Código: {code})\n"
                conn.sendall(resposta.encode())

            elif cmd_lobby == "CRIAR":
                if len(parts) < 2:
                    conn.sendall("CRIAR_R Formato inválido.\n".encode())
                    continue
                
                titulo = parts[1]
                users = load_data(USERS_FILE)
                listas = load_data(LISTAS_FILE)
                
                new_code = generate_code()
                while new_code in listas: new_code = generate_code()
                
                listas[new_code] = {"titulo": titulo, "tarefas": []}
                users[logged_user]["listas_acessiveis"].append(new_code)
                
                save_data(LISTAS_FILE, listas)
                save_data(USERS_FILE, users)
                
                conn.sendall(f"CRIAR_R Lista '{titulo}' criada! Código: {new_code}\n".encode())

            elif cmd_lobby == "ENTRAR":
                if len(parts) < 2:
                    conn.sendall("ENTRAR_R Formato inválido.\n".encode())
                    continue
                
                code_to_join = parts[1].upper()
                users = load_data(USERS_FILE)
                listas = load_data(LISTAS_FILE)

                if code_to_join not in listas:
                    conn.sendall("ENTRAR_R Código de lista inválido.\n".encode())
                
                elif code_to_join not in users[logged_user]["listas_acessiveis"]:
                    users[logged_user]["listas_acessiveis"].append(code_to_join)
                    save_data(USERS_FILE, users)
                    titulo = listas[code_to_join]["titulo"]
                    conn.sendall(f"ENTRAR_R Adicionado à lista: '{titulo}'. Entre novamente para ver.\n".encode())
                
                else: 
                    # --- ESTADO 3: ENTRAR NO MODO LISTA ---
                    titulo_lista = listas[code_to_join]["titulo"]
                    conn.sendall(f"MODO_LISTA {titulo_lista}\n".encode())
                    
                    while True:
                        list_data = conn.recv(1024).decode().strip()
                        if not list_data:
                            raise ConnectionResetError
                        
                        if list_data.upper() == "VOLTAR":
                            conn.sendall("MODO_LOBBY Voltando ao Lobby...\n".encode())
                            break 
                        
                        # --- Processa o comando da lista (agora com JSON) ---
                        response = process_list_command(list_data, code_to_join, logged_user)
                        conn.sendall(response.encode())

            elif cmd_lobby == "SAIR":
                print(f"👋 [{logged_user}] Fez logout.")
                conn.sendall("Até logo!\n".encode())
                return 
            
            else:
                conn.sendall("ERRO Comando de Lobby inválido.\n".encode())

    except (ConnectionResetError, socket.error):
        print(f"[{addr}] Ligação perdida.")
    except Exception as e:
        print(f"*** ERRO INESPERADO: {e} ***")
    finally:
        conn.close()
        print(f"[DESCONECTADO] {addr}")


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
        print("\n[DESLIGANDO] Recebido Ctrl+C. A desligar...")
    finally:
        server.close()
        print("[SERVIDOR DESLIGADO]")

if __name__ == "__main__":
    start()