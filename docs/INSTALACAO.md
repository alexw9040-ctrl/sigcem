# SIGCEM — instalação local

## Execução rápida

1. Instale Python 3.12 ou superior.
2. Crie um ambiente virtual: `python -m venv .venv`.
3. Ative-o e instale: `pip install -r requirements.txt`.
4. Execute `python app.py`.
5. Abra `http://127.0.0.1:3000`.
6. No primeiro acesso, crie o usuário administrador. Não existe senha padrão.

O banco SQLite é criado em `data/sigcem.db`. Documentos ficam em `data/uploads` e cópias de segurança em `data/backups`.

## Rede local

Execute em um computador/servidor da Prefeitura e permita a porta 3000 apenas na rede interna. Para múltiplos usuários, planeje PostgreSQL e armazenamento compartilhado de documentos antes de produção.

## Backup

Use o módulo **Backup e segurança** para criar uma cópia completa. Antes de restaurar, o sistema cria uma cópia de segurança do estado atual e exige confirmação.

## Primeiro acesso

O formulário de inicialização cria o administrador e grava apenas um hash de senha. O usuário deve trocar/gerenciar credenciais pela área de usuários.

## Avisos de produção

Defina política de retenção documental, perfis, tabela de taxas, regras de exumação, modelos oficiais, rotina de backup externo e responsável institucional antes do uso com dados reais. Valide obrigações locais com a assessoria jurídica e o encarregado de dados.
