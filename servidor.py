import socket
import threading

tasks = [] 
lock = threading.Lock()  

HOST = "0.0.0.0"
PORT = 5050

def handle_client(conn, addr):
    print(f"[NOVA CONEXAO] {addr} conectado.")
    conn.sendall("Bem-vindo à ShareList!\n".encode())

    try:
        while True:
            data = conn.recv(1024).decode().strip()
            
            if not data:
                break 

            print(f"[{addr}] Enviou: {data}")

            
            try:
                with lock:
                    response = process_command(data)

            except Exception as e:
                print(f"*** ERRO NO SERVIDOR: {e} ***")
                response = "ERRO: Ocorreu um erro interno no servidor.\n"
            
            conn.sendall(response.encode())
        
            if data.upper() == "SAIR":
                break

    except ConnectionResetError:
        print(f"[{addr}] Ligação perdida abruptamente.")

    except Exception as e:
        print(f"[{addr}] Erro de rede: {e}")

    finally:
        conn.close()
        print(f"[DESCONECTADO] {addr}")

def process_command(msg):
    parts = msg.split(" ", 1)
    cmd = parts[0].upper()

    if cmd == "ADD" and len(parts) > 1:
        tasks.append({"desc": parts[1], "done": False})
        return "Tarefa adicionada!\n"

    elif cmd == "LIST":
        if not tasks:
            return "Nenhuma tarefa.\n"
        return "\n".join([f"{i+1} - {'[x]' if t['done'] else '[ ]'} {t['desc']}" for i, t in enumerate(tasks)]) + "\n"

    elif cmd == "DONE" and len(parts) > 1:
        try:
            i = int(parts[1]) - 1
            tasks[i]["done"] = True
            return f"OK Tarefa {i+1} concluída\n"
        
        except (ValueError, IndexError):
            return "Erro: índice inválido.\n"

    elif cmd == "DEL" and len(parts) > 1:
        try:
            i = int(parts[1]) - 1
            tasks.pop(i)
            return f"OK Tarefa {i+1} removida\n"
        
        except (ValueError, IndexError):
            return "Erro: índice inválido.\n"

    elif cmd == "SAIR":
        return "Tchau!\n" 

    return "Comando desconhecido.\n" 

def start():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVIDOR] Rodando em {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

if __name__ == "__main__":
    start()