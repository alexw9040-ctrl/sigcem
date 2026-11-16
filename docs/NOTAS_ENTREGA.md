# Notas da entrega SIGCEM

## Entregue

O SIGCEM está estruturado como aplicação Flask local-first, com SQLite relacional, autenticação, perfis, auditoria, cadastros, operações de sepultamento e movimentação, documentos, protocolos, financeiro configurável, relatórios, importação, backup/restauração e operação sem internet no ambiente local.

A entrega começa sem dados reais e exige a criação do primeiro administrador no primeiro acesso. Antes do uso oficial, a Administração deve configurar identidade institucional, permissões, serviços/taxas, modelos documentais, política de retenção, rotina de backup externo e regras municipais.

## Limites conhecidos

- O empacotamento instalável para Windows 10/11 (por exemplo, Tauri) é uma etapa posterior de distribuição; o núcleo local/offline já funciona via Python/Flask.
- A operação multiestação em rede municipal e sincronização online opcional exigem uma etapa específica de infraestrutura, autenticação compartilhada e migração para PostgreSQL.
- QR Code interno não foi acoplado ao núcleo nesta versão para evitar dependência adicional. Pode ser adicionado em etapa posterior apontando para identificadores internos protegidos, sem CPF, RG ou documentos pessoais.
- O backup automático configurável nesta versão registra a preferência operacional; a execução agendada deve ser definida pela política de implantação (Agendador de Tarefas do Windows, serviço local ou rotina administrativa).

## Segurança e governança

Não use a aplicação com dados reais sem trocar o segredo local, configurar usuários individuais, limitar perfis, testar restauração e validar os procedimentos com o encarregado de dados e o jurídico municipal.
