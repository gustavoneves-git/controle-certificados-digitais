import getpass

from werkzeug.security import generate_password_hash


def main():
    senha = getpass.getpass("Senha para gerar hash: ")
    confirmacao = getpass.getpass("Confirme a senha: ")
    if senha != confirmacao:
        print("As senhas nao conferem.")
        return 1
    print(generate_password_hash(senha))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
