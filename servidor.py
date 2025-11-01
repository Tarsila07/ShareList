# servidor.py
import socket
import threading

tasks = []  # lista compartilhada
lock = threading.Lock()  # evita conflito de acesso

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
            
            # ATUALIZADO: Verificamos o 'SAIR' que o cliente envia
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
        return "OK Tarefa adicionada\n"

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

    # ATUALIZADO: O comando que o servidor espera
    elif cmd == "SAIR": 
        return "BYE\n" # O servidor confirma a saída

    return "Comando desconhecido.\n" 

def start():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # --- (FIX DO CTRL+C) ---
    # Define um timeout de 1.0 segundos no socket do servidor
    # Isto faz com que 'server.accept()' deixe de ser 100% bloqueante
    server.settimeout(1.0)
    
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVIDOR] Rodando em {HOST}:{PORT}")

    try:
        while True:
            # --- (FIX DO CTRL+C) ---
            # Agora, o accept() está dentro de um try/except próprio
            try:
                # Tenta aceitar uma ligação (isto agora vai falhar
                # com um 'timeout' a cada 1 segundo, o que é bom)
                conn, addr = server.accept()
                
                # Se uma ligação for aceite, corre o código normal:
                thread = threading.Thread(target=handle_client, args=(conn, addr))
                thread.start()
            
            except socket.timeout:
                # Quando o timeout de 1s acontece, apanhamos o erro
                # e não fazemos nada ('pass').
                # Isto permite que o 'while True' continue e dê ao 
                # Python a chance de "ouvir" o Ctrl+C.
                pass 
            
    except KeyboardInterrupt:
        # Agora, quando premir Ctrl+C, o Python consegue
        # apanhar o 'KeyboardInterrupt' e sair do 'while True'.
        print("\n[DESLIGANDO] Recebido Ctrl+C. A desligar...")
        
    finally:
        # Limpa o socket antes de fechar
        server.close()
        print("[SERVIDOR DESLIGADO]")


if __name__ == "__main__":
    start()