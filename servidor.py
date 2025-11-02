import socket
import threading
import json
import os
import random
import string

HOST = "0.0.0.0"
PORT = 5050
USERS_FILE = "users.json"
LISTAS_FILE = "listas.json"
lock = threading.Lock()


def load_data(filepath):
    with lock:
        if not os.path.exists(filepath):
            with open(filepath, "w") as f:
                json.dump({}, f)
            return {}
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"*** ERRO: Ficheiro {filepath} corrompido! A criar um novo.")
            with open(filepath, "w") as f:
                json.dump({}, f)
            return {}


def save_data(filepath, data):
    with lock:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)


def generate_code(length=4):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def process_list_command(msg, list_code, user):
    listas = load_data(LISTAS_FILE)
    if list_code not in listas:
        return "⚠️ ERRO: A lista em que estava foi apagada.\n"

    current_tasks = listas[list_code]["tarefas"]
    parts = msg.split(" ", 1)
    cmd = parts[0].upper()
    response = "❓ Comando desconhecido.\n"

    # ADD
    if cmd == "ADD" and len(parts) > 1:
        tarefa_desc = parts[1]
        current_tasks.append({"desc": tarefa_desc, "done": False})
        print(f"[{user}] Adicionou '{tarefa_desc}' à lista '{list_code}'")
        response = "✅ Tarefa adicionada.\n"

    # LIST
    elif cmd == "LIST":
        print(f"[{user}] Solicitou a lista '{list_code}'")
        if not current_tasks:
            response = "📭 Nenhuma tarefa nesta lista.\n"
        else:
            response = "\n".join([
                f"{i+1}. {'[✔]' if t['done'] else '[ ]'} {t['desc']}"
                for i, t in enumerate(current_tasks)
            ]) + "\n"

    # DONE
    elif cmd == "DONE":
        if len(parts) == 1:
            response = "⚠️ Use: DONE (número do item). Ex: DONE 2\n"
        else:
            try:
                i = int(parts[1]) - 1
                current_tasks[i]["done"] = True
                print(f"[{user}] Concluiu '{current_tasks[i]['desc']}' na lista '{list_code}'")
                response = f"✅ Tarefa {i+1} marcada como concluída.\n"
            except (ValueError, IndexError):
                response = "❌ Índice inválido. Use: DONE (número do item)\n"

    # DEL
    elif cmd == "DEL":
        if len(parts) == 1:
            response = "⚠️ Use: DEL (número do item). Ex: DEL 3\n"
        else:
            try:
                i = int(parts[1]) - 1
                tarefa_removida = current_tasks.pop(i)
                print(f"[{user}] Removeu '{tarefa_removida['desc']}' da lista '{list_code}'")
                response = f"🗑️ Tarefa '{tarefa_removida['desc']}' removida.\n"
            except (ValueError, IndexError):
                response = "❌ Índice inválido. Use: DEL (número do item)\n"

    if cmd in ["ADD", "DONE", "DEL"]:
        save_data(LISTAS_FILE, listas)

    return response


def handle_client(conn, addr):
    print(f"[NOVA CONEXAO] {addr} conectado.")
    conn.sendall("Bem-vindo à ShareList!\n".encode())
    logged_user = None

    try:
        # LOGIN / REGISTRO
        while not logged_user:
            conn.sendall("Usuário: ".encode())
            user = conn.recv(1024).decode().strip()
            if not user:
                continue

            users = load_data(USERS_FILE)

            if user in users:
                conn.sendall("Senha: ".encode())
                pwd = conn.recv(1024).decode().strip()
                if not pwd:
                    continue
                if users[user]["password"] == pwd:
                    logged_user = user
                    conn.sendall(f"✅ Login bem-sucedido! Bem-vindo, {user}.\n".encode())
                    print(f"[{user}] fez login com sucesso.")
                else:
                    conn.sendall("❌ Senha incorreta.\n".encode())
            else:
                conn.sendall(f"❌ Usuário '{user}' não existe. Deseja registrar (S/N)? ".encode())
                choice = conn.recv(1024).decode().strip().upper()
                if choice == "S":
                    conn.sendall("Nova Senha: ".encode())
                    pwd = conn.recv(1024).decode().strip()
                    if not pwd:
                        conn.sendall("❌ Criação cancelada (senha vazia).\n".encode())
                        continue
                    users[user] = {"password": pwd, "listas_acessiveis": []}
                    save_data(USERS_FILE, users)
                    logged_user = user
                    conn.sendall(f"✅ Usuário {user} registrado com sucesso!\n".encode())
                    print(f"[{user}] registrou uma nova conta.")
                else:
                    conn.sendall("OK. Tente novamente.\n".encode())

        # MENU PRINCIPAL
        menu_lobby = (
            f"\n--- [LOBBY PRINCIPAL: {logged_user}] ---\n"
            "1- Ver minhas listas\n"
            "2- Criar uma nova lista\n"
            "3- Entrar em uma lista (por código)\n"
            "4- Sair (Logout)\n"
            "--------------------------\n"
            "Digite (1-4): "
        )

        while True:
            conn.sendall(menu_lobby.encode())
            choice = conn.recv(1024).decode().strip()
            if not choice:
                break

            if choice == "1":
                users = load_data(USERS_FILE)
                listas = load_data(LISTAS_FILE)
                user_list_codes = users[logged_user]["listas_acessiveis"]
                if not user_list_codes:
                    conn.sendall("📭 Você não tem listas.\n".encode())
                    continue
                resposta = "📋 Suas Listas:\n"
                for i, code in enumerate(user_list_codes, 1):
                    titulo = listas.get(code, {}).get("titulo", f"Lista {code} (Apagada)")
                    resposta += f" {i}. {titulo} (Código: {code})\n"
                conn.sendall(resposta.encode())

            elif choice == "2":
                conn.sendall("Digite o título da nova lista: ".encode())
                titulo = conn.recv(1024).decode().strip()
                if not titulo:
                    conn.sendall("❌ Criação cancelada (título vazio).\n".encode())
                    continue
                users = load_data(USERS_FILE)
                listas = load_data(LISTAS_FILE)
                new_code = generate_code()
                while new_code in listas:
                    new_code = generate_code()
                listas[new_code] = {"titulo": titulo, "tarefas": []}
                users[logged_user]["listas_acessiveis"].append(new_code)
                save_data(LISTAS_FILE, listas)
                save_data(USERS_FILE, users)
                conn.sendall(f"✅ Lista '{titulo}' criada! Código de partilha: {new_code}\n".encode())

            elif choice == "3":
                conn.sendall("Digite o código da lista: ".encode())
                code_to_join = conn.recv(1024).decode().strip().upper()
                if not code_to_join:
                    conn.sendall("❌ Entrada cancelada (código vazio).\n".encode())
                    continue

                users = load_data(USERS_FILE)
                listas = load_data(LISTAS_FILE)

                if code_to_join not in listas:
                    conn.sendall("❌ Código de lista inválido.\n".encode())
                elif code_to_join not in users[logged_user]["listas_acessiveis"]:
                    users[logged_user]["listas_acessiveis"].append(code_to_join)
                    save_data(USERS_FILE, users)
                    titulo = listas[code_to_join]["titulo"]
                    conn.sendall(f"✅ Você foi adicionado à lista '{titulo}'. Use a opção 3 novamente para editá-la.\n".encode())
                else:
                    titulo_lista = listas[code_to_join]["titulo"]
                    comandos = (
                        "\n🧾 COMANDOS DISPONÍVEIS 🧾\n"
                        "--------------------------------\n"
                        "📌 ADD  'descrição'        → Adiciona uma tarefa\n"
                        "☑️  DONE 'número'          → Marca como concluída\n"
                        "🗑️  DEL 'número'           → Deleta uma tarefa\n"
                        "📋 LIST                    → Mostra as tarefas\n"
                        "↩️  VOLTAR                 → Sai da lista\n"
                        "--------------------------------\n"
                    )
                    conn.sendall(f"✅ Entrando na lista '{titulo_lista}'...\n{comandos}".encode())

                    while True:
                        conn.sendall(f"({logged_user}) [{titulo_lista}] >> ".encode())
                        list_data = conn.recv(1024).decode().strip()
                        if not list_data:
                            raise ConnectionResetError
                        if list_data.upper() == "VOLTAR":
                            conn.sendall("↩️ Saindo da lista...\n".encode())
                            break
                        response = process_list_command(list_data, code_to_join, logged_user)
                        conn.sendall(response.encode())

            elif choice == "4":
                print(f"[{logged_user}] Fez logout.")
                conn.sendall("Até logo!\n".encode())
                return
            else:
                conn.sendall("❌ Opção inválida. Digite um número de 1 a 4.\n".encode())

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
    print(f"[SERVIDOR] Rodando em {HOST}:{PORT}")
    try:
        while True:
            try:
                conn, addr = server.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr))
                thread.start()
            except socket.timeout:
                pass
    except KeyboardInterrupt:
        print("\n[DESLIGANDO] Recebido Ctrl+C. Encerrando...")
    finally:
        server.close()
        print("[SERVIDOR DESLIGADO]")


if __name__ == "__main__":
    start()
