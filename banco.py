import sqlite3
import hashlib
import secrets
import re
from getpass import getpass
import os

class BancoDigital:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.usuario_logado = None
        self.criar_banco()

    def conectar(self):
        """Conecta ao banco de dados"""
        try:
            self.conn = sqlite3.connect('banco.db')
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print(f"Erro ao conectar ao banco de dados: {e}")
            raise

    def desconectar(self):
        """Desconecta do banco de dados"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def criar_banco(self):
        """Cria o banco de dados e tabelas com todas as colunas necessárias"""
        try:
            self.conectar()
            
            # Tabela de usuários com todas colunas necessárias
            self.cursor.execute(''' 
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                senha TEXT NOT NULL,
                salt TEXT NOT NULL,
                saldo REAL NOT NULL DEFAULT 0,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ativo BOOLEAN DEFAULT 1
            )
            ''')

            # Tabela de transações
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_origem INTEGER NOT NULL,
                id_destino INTEGER NOT NULL,
                valor REAL NOT NULL,
                descricao TEXT,
                data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(id_origem) REFERENCES usuarios(id),
                FOREIGN KEY(id_destino) REFERENCES usuarios(id),
                CHECK (valor > 0)
            )
            ''')
            
            self.conn.commit()
            
        except sqlite3.Error as e:
            print(f"Erro ao criar banco de dados: {e}")
            raise
        finally:
            self.desconectar()

    def gerar_salt(self):
        """Gera um salt aleatório para a senha"""
        return secrets.token_hex(16)

    def hash_senha(self, senha, salt):
        """Cria um hash seguro da senha usando PBKDF2"""
        if isinstance(senha, str):
            senha = senha.encode()
        return hashlib.pbkdf2_hmac('sha256', senha, salt.encode(), 100000).hex()

    def validar_email(self, email):
        """Valida o formato do email"""
        regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(regex, email) is not None

    def validar_senha(self, senha):
        """Valida a força da senha"""
        if len(senha) < 8:
            return False
        if not any(c.isupper() for c in senha):
            return False
        if not any(c.isdigit() for c in senha):
            return False
        return True

    def cadastrar_usuario(self, nome, email, senha):
        """Cadastra um novo usuário"""
        if not self.validar_email(email):
            print("Erro: Email inválido.")
            return False

        if not self.validar_senha(senha):
            print("Erro: Senha deve ter pelo menos 8 caracteres, uma letra maiúscula e um número.")
            return False

        try:
            self.conectar()
            
            self.cursor.execute('SELECT id FROM usuarios WHERE email = ?', (email,))
            if self.cursor.fetchone():
                print("Erro: Email já cadastrado.")
                return False

            salt = self.gerar_salt()
            senha_hash = self.hash_senha(senha, salt)

            self.cursor.execute('''
            INSERT INTO usuarios (nome, email, senha, salt)
            VALUES (?, ?, ?, ?)
            ''', (nome, email, senha_hash, salt))

            self.conn.commit()
            print("Usuário cadastrado com sucesso!")
            return True

        except sqlite3.Error as e:
            print(f"Erro ao cadastrar usuário: {e}")
            return False
        finally:
            self.desconectar()

    def login_usuario(self, email, senha):
        """Realiza o login do usuário"""
        try:
            self.conectar()
            
            self.cursor.execute('''
            SELECT id, nome, senha, salt, saldo FROM usuarios 
            WHERE email = ? AND ativo = 1
            ''', (email,))
            
            usuario = self.cursor.fetchone()
            
            if usuario:
                senha_hash = self.hash_senha(senha, usuario[3])
                if senha_hash == usuario[2]:
                    self.usuario_logado = {
                        'id': usuario[0],
                        'nome': usuario[1],
                        'saldo': usuario[4]
                    }
                    print(f"Bem-vindo, {usuario[1]}! Seu saldo é: R${usuario[4]:.2f}")
                    return True
                
            print("Email ou senha inválidos.")
            return False
            
        except sqlite3.Error as e:
            print(f"Erro ao fazer login: {e}")
            return False
        finally:
            self.desconectar()

    def adicionar_saldo(self, valor):
        """Adiciona saldo à conta do usuário"""
        if not self.usuario_logado:
            print("Erro: Nenhum usuário logado.")
            return False

        if valor <= 0:
            print("Erro: Valor deve ser positivo.")
            return False

        try:
            self.conectar()
            
            self.cursor.execute('''
            UPDATE usuarios SET saldo = saldo + ? 
            WHERE id = ?
            ''', (valor, self.usuario_logado['id']))
            
            self.cursor.execute('''
            INSERT INTO transacoes (id_origem, id_destino, valor, descricao)
            VALUES (?, ?, ?, ?)
            ''', (self.usuario_logado['id'], self.usuario_logado['id'], valor, 'Depósito'))
            
            self.conn.commit()
            
            self.usuario_logado['saldo'] += valor
            print(f"R${valor:.2f} adicionados com sucesso. Novo saldo: R${self.usuario_logado['saldo']:.2f}")
            return True
            
        except sqlite3.Error as e:
            print(f"Erro ao adicionar saldo: {e}")
            return False
        finally:
            self.desconectar()

    def transferencia(self, destino_email, valor, descricao=""):
        """Realiza uma transferência para outro usuário"""
        if not self.usuario_logado:
            print("Erro: Nenhum usuário logado.")
            return False

        if valor <= 0:
            print("Erro: Valor deve ser positivo.")
            return False

        if valor > 10000:
            print("Erro: Valor máximo por transferência é R$10.000,00.")
            return False

        try:
            self.conectar()
            
            self.cursor.execute('SELECT saldo FROM usuarios WHERE id = ?', (self.usuario_logado['id'],))
            saldo = self.cursor.fetchone()[0]
            
            if saldo < valor:
                print("Erro: Saldo insuficiente.")
                return False

            self.cursor.execute('SELECT id, nome FROM usuarios WHERE email = ? AND ativo = 1', (destino_email,))
            destino = self.cursor.fetchone()
            
            if not destino:
                print("Erro: Conta destino não encontrada ou inativa.")
                return False

            if destino[0] == self.usuario_logado['id']:
                print("Erro: Não pode transferir para si mesmo.")
                return False

            self.conn.execute("BEGIN TRANSACTION")
            
            try:
                self.cursor.execute('UPDATE usuarios SET saldo = saldo - ? WHERE id = ?', 
                                  (valor, self.usuario_logado['id']))
                self.cursor.execute('UPDATE usuarios SET saldo = saldo + ? WHERE id = ?', 
                                  (valor, destino[0]))
                
                self.cursor.execute('''
                INSERT INTO transacoes (id_origem, id_destino, valor, descricao)
                VALUES (?, ?, ?, ?)
                ''', (self.usuario_logado['id'], destino[0], valor, descricao))
                
                self.conn.commit()
                
                self.usuario_logado['saldo'] -= valor
                print(f"Transferência de R${valor:.2f} para {destino[1]} realizada com sucesso!")
                return True
                
            except sqlite3.Error:
                self.conn.rollback()
                raise
                
        except sqlite3.Error as e:
            print(f"Erro na transferência: {e}")
            return False
        finally:
            self.desconectar()

    def extrato(self, limite=10):
        """Exibe o extrato de transações do usuário"""
        if not self.usuario_logado:
            print("Erro: Nenhum usuário logado.")
            return False

        try:
            self.conectar()
            
            self.cursor.execute('''
            SELECT t.data, 
                   CASE WHEN t.id_origem = ? THEN 'Enviado' ELSE 'Recebido' END as tipo,
                   CASE WHEN t.id_origem = ? THEN u_destino.nome ELSE u_origem.nome END as contraparte,
                   t.valor, t.descricao
            FROM transacoes t
            JOIN usuarios u_origem ON u_origem.id = t.id_origem
            JOIN usuarios u_destino ON u_destino.id = t.id_destino
            WHERE t.id_origem = ? OR t.id_destino = ?
            ORDER BY t.data DESC
            LIMIT ?
            ''', (self.usuario_logado['id'], self.usuario_logado['id'], 
                  self.usuario_logado['id'], self.usuario_logado['id'], limite))
            
            transacoes = self.cursor.fetchall()
            
            if transacoes:
                print("\n=== EXTRATO BANCÁRIO ===")
                print(f"{'Data':<20} {'Tipo':<10} {'Contraparte':<20} {'Valor':>10} {'Descrição'}")
                print("-" * 70)
                for t in transacoes:
                    valor_formatado = f"R${t[3]:.2f}"
                    if t[1] == 'Enviado':
                        valor_formatado = f"-{valor_formatado}"
                    else:
                        valor_formatado = f"+{valor_formatado}"
                    
                    print(f"{t[0]:<20} {t[1]:<10} {t[2]:<20} {valor_formatado:>10} {t[4]}")
            else:
                print("Nenhuma transação encontrada.")
                
            return True
            
        except sqlite3.Error as e:
            print(f"Erro ao obter extrato: {e}")
            return False
        finally:
            self.desconectar()

    def saldo(self):
        """Exibe o saldo atual"""
        if self.usuario_logado:
            print(f"Saldo atual: R${self.usuario_logado['saldo']:.2f}")
            return True
        else:
            print("Erro: Nenhum usuário logado.")
            return False

    def deletar_conta(self, confirmacao):
        """Desativa a conta do usuário"""
        if not self.usuario_logado:
            print("Erro: Nenhum usuário logado.")
            return False

        if confirmacao.lower() != 'sim':
            print("Cancelado: Confirmação necessária.")
            return False

        try:
            self.conectar()
            
            self.cursor.execute('UPDATE usuarios SET ativo = 0 WHERE id = ?', 
                              (self.usuario_logado['id'],))
            
            self.conn.commit()
            print("Sua conta foi desativada com sucesso.")
            self.usuario_logado = None
            return True
            
        except sqlite3.Error as e:
            print(f"Erro ao deletar conta: {e}")
            return False
        finally:
            self.desconectar()

    def menu_principal(self):
        """Exibe o menu principal"""
        while True:
            print("\n=== BANCO DIGITAL ===")
            print("1. Cadastrar")
            print("2. Login")
            print("3. Sair")
            
            opcao = input("Escolha uma opção: ")
            
            if opcao == '1':
                nome = input("Nome completo: ")
                email = input("Email: ")
                senha = getpass("Senha (mínimo 8 caracteres, 1 maiúscula e 1 número): ")
                self.cadastrar_usuario(nome, email, senha)
                
            elif opcao == '2':
                email = input("Email: ")
                senha = getpass("Senha: ")
                if self.login_usuario(email, senha):
                    self.menu_usuario()
                    
            elif opcao == '3':
                print("Obrigado por usar nosso banco digital!")
                break
                
            else:
                print("Opção inválida.")

    def menu_usuario(self):
        """Exibe o menu do usuário logado"""
        while self.usuario_logado:
            print(f"\nBem-vindo, {self.usuario_logado['nome']}!")
            print("1. Ver Saldo")
            print("2. Extrato")
            print("3. Depositar")
            print("4. Transferir")
            print("5. Deletar Conta")
            print("6. Sair")
            
            opcao = input("Escolha uma opção: ")
            
            if opcao == '1':
                self.saldo()
                
            elif opcao == '2':
                self.extrato()
                
            elif opcao == '3':
                try:
                    valor = float(input("Valor a depositar: R$"))
                    self.adicionar_saldo(valor)
                except ValueError:
                    print("Erro: Valor inválido.")
                    
            elif opcao == '4':
                try:
                    destino = input("Email do destinatário: ")
                    valor = float(input("Valor a transferir: R$"))
                    descricao = input("Descrição (opcional): ")
                    self.transferencia(destino, valor, descricao)
                except ValueError:
                    print("Erro: Valor inválido.")
                    
            elif opcao == '5':
                confirmacao = input("Digite 'sim' para confirmar a exclusão da conta: ")
                if self.deletar_conta(confirmacao):
                    break
                    
            elif opcao == '6':
                self.usuario_logado = None
                print("Logout realizado com sucesso.")
                break
                
            else:
                print("Opção inválida.")

if __name__ == "__main__":
    banco = BancoDigital()
    banco.menu_principal()