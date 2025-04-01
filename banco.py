import sqlite3
import hashlib

# função para criar o banco de dados e as tabelas
def criar_banco():
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()

    # criar tabela de usuários
    cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        senha TEXT NOT NULL,
        saldo REAL NOT NULL DEFAULT 0
    )
    ''')

    # criar tabela de transações
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_origem INTEGER NOT NULL,
        id_destino INTEGER NOT NULL,
        valor REAL NOT NULL,
        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(id_origem) REFERENCES usuarios(id),
        FOREIGN KEY(id_destino) REFERENCES usuarios(id)
    )
    ''')

    conn.commit()
    conn.close()

# função para cadastrar um novo usuário
def cadastrar_usuario(nome, email, senha):
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()

    # criptografar a senha
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()

    try:
        cursor.execute('''
        INSERT INTO usuarios (nome, email, senha)
        VALUES (?, ?, ?)
        ''', (nome, email, senha_hash))

        conn.commit()
        print("Usuário cadastrado com sucesso!")

    except sqlite3.IntegrityError:
        print("Erro: O email já está registrado.")

    conn.close()

# função de login de usuário
def login_usuario(email, senha):
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()

    # criptografar a senha fornecida
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()

    cursor.execute('''
    SELECT id, nome, saldo FROM usuarios
    WHERE email = ? AND senha = ?
    ''', (email, senha_hash))

    usuario = cursor.fetchone()

    conn.close()

    if usuario:
        print(f"Bem-vindo, {usuario[1]}! Seu saldo é: R${usuario[2]:.2f}")
        return usuario[0]  # Retorna o ID do usuário para futuras transações
    else:
        print("Email ou senha inválidos.")
        return None

# função para adicionar saldo
def adicionar_saldo(usuario_id, valor):
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()

    # verificar se o valor é positivo
    if valor <= 0:
        print("Erro: O valor a ser adicionado deve ser maior que zero.")
        conn.close()
        return

    # atualizar saldo do usuário
    cursor.execute('''
    UPDATE usuarios SET saldo = saldo + ? WHERE id = ?
    ''', (valor, usuario_id))

    conn.commit()
    print(f"R${valor:.2f} adicionados ao seu saldo com sucesso!")

    # exibir o saldo atualizado
    cursor.execute('''
    SELECT saldo FROM usuarios WHERE id = ?
    ''', (usuario_id,))
    saldo_atual = cursor.fetchone()
    print(f"Seu saldo atualizado é: R${saldo_atual[0]:.2f}")

    conn.close()

# função para realizar transferência bancária
def transferencia(usuario_origem_id, usuario_destino_email, valor):
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()

    # verificar se o valor da transferência é válido
    if valor <= 0:
        print("Erro: O valor da transferência deve ser maior que zero.")
        conn.close()
        return

    # buscar o saldo do usuário de origem
    cursor.execute('''
    SELECT saldo FROM usuarios WHERE id = ?
    ''', (usuario_origem_id,))
    saldo_origem = cursor.fetchone()

    if saldo_origem is None or saldo_origem[0] < valor:
        print("Erro: Saldo insuficiente.")
        conn.close()
        return

    # verificar se o email de destino existe no banco de dados
    cursor.execute('''
    SELECT id FROM usuarios WHERE email = ?
    ''', (usuario_destino_email,))
    usuario_destino = cursor.fetchone()

    if usuario_destino is None:
        print("Erro: A conta de destino não foi criada ainda.")
        conn.close()
        return

    # atualizar saldo dos dois usuários
    cursor.execute('''
    UPDATE usuarios SET saldo = saldo - ? WHERE id = ?
    ''', (valor, usuario_origem_id))

    cursor.execute('''
    UPDATE usuarios SET saldo = saldo + ? WHERE id = ?
    ''', (valor, usuario_destino[0]))

    # Registrar a transação
    cursor.execute('''
    INSERT INTO transacoes (id_origem, id_destino, valor)
    VALUES (?, ?, ?)
    ''', (usuario_origem_id, usuario_destino[0], valor))

    conn.commit()
    print(f"Transferência de R${valor:.2f} realizada com sucesso!")

    conn.close()

# função para exibir o histórico de transferências
def exibir_historico(usuario_id):
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()

    # consultar transações do usuário, tanto como origem quanto como destino
    cursor.execute('''
    SELECT t.data, u_origem.nome AS origem, u_destino.nome AS destino, t.valor
    FROM transacoes t
    JOIN usuarios u_origem ON u_origem.id = t.id_origem
    JOIN usuarios u_destino ON u_destino.id = t.id_destino
    WHERE t.id_origem = ? OR t.id_destino = ?
    ORDER BY t.data DESC
    ''', (usuario_id, usuario_id))

    transacoes = cursor.fetchall()

    if transacoes:
        print("\nHistórico de Transferências:")
        for transacao in transacoes:
            print(f"Data: {transacao[0]}, De: {transacao[1]} Para: {transacao[2]}, Valor: R${transacao[3]:.2f}")
    else:
        print("Nenhuma transação encontrada.")

    conn.close()

# função para ver o saldo atual
def ver_saldo(usuario_id):
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()

    # consultar o saldo do usuário
    cursor.execute('''
    SELECT saldo FROM usuarios WHERE id = ?
    ''', (usuario_id,))
    saldo = cursor.fetchone()

    if saldo:
        print(f"Seu saldo atual é: R${saldo[0]:.2f}")
    else:
        print("Erro: Usuário não encontrado.")

    conn.close()

# função para deletar a conta
def deletar_conta(usuario_id):
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()

    # excluir transações relacionadas ao usuário
    cursor.execute('''
    DELETE FROM transacoes WHERE id_origem = ? OR id_destino = ?
    ''', (usuario_id, usuario_id))

    # excluir o usuário
    cursor.execute('''
    DELETE FROM usuarios WHERE id = ?
    ''', (usuario_id,))

    conn.commit()
    print("Sua conta foi deletada com sucesso!")

    conn.close()

# função para exibir o menu principal
def menu():
    while True:
        print("\n1. Cadastro")
        print("2. Login")
        print("3. Sair")

        escolha = input("Escolha uma opção: ")

        if escolha == '1':
            nome = input("Nome: ")
            email = input("Email: ")
            senha = input("Senha: ")
            cadastrar_usuario(nome, email, senha)
        elif escolha == '2':
            email = input("Email: ")
            senha = input("Senha: ")
            usuario_id = login_usuario(email, senha)
            if usuario_id:
                while True:
                    print("\n1. Realizar Transferência")
                    print("2. Adicionar Saldo")
                    print("3. Ver Saldo Atual")
                    print("4. Ver Histórico de Transferências")
                    print("5. Deletar Conta")
                    print("6. Sair")
                    escolha = input("Escolha uma opção: ")
                    if escolha == '1':
                        destino_email = input("Email do destinatário: ")
                        valor = float(input("Valor da transferência: "))
                        transferencia(usuario_id, destino_email, valor)
                    elif escolha == '2':
                        valor = float(input("Valor a ser adicionado ao saldo: "))
                        adicionar_saldo(usuario_id, valor)
                    elif escolha == '3':
                        ver_saldo(usuario_id)
                    elif escolha == '4':
                        exibir_historico(usuario_id)
                    elif escolha == '5':
                        deletar = input("Tem certeza que deseja deletar sua conta? (s/n): ")
                        if deletar.lower() == 's':
                            deletar_conta(usuario_id)
                            break
                    elif escolha == '6':
                        break
        elif escolha == '3':
            break
        else:
            print("Opção inválida.")

# criar o banco de dados e tabelas
criar_banco()

# executar o menu
menu()
