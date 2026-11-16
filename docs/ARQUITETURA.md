# Arquitetura técnica

O SIGCEM é um monólito modular Flask com SQLite local-first. `app.py` concentra as rotas e regras de negócio até a primeira estabilização; a separação futura pode mover domínio, repositórios e serviços para pacotes sem alterar as rotas.

As tabelas têm chaves estrangeiras e registros de auditoria. `deleted_at` preserva históricos. O fluxo de sepultamento usa transação e calcula ocupação pela tabela `burials`, evitando dupla ocupação.

A migração para PostgreSQL deve preservar nomes e tipos principais. O empacotamento Windows pode usar Tauri apontando para um executável local do backend, ou PyInstaller como alternativa operacional.
