# SIGCEM — resultados de entrega

- [x] **Base local-first e instalação inicial**
  - A aplicação roda sem internet em `0.0.0.0:3000`/localhost usando SQLite local.
  - O primeiro acesso cria um administrador com senha definida no momento da instalação, sem senha padrão permanente.
  - Instituição, município, cemitério, endereço e identidade visual são configuráveis.

- [x] **Login, usuários, perfis e auditoria**
  - Usuário ou e-mail institucional, senha com visualização, sessão, bloqueio e controle de tentativas.
  - Perfis administrador geral, administrador do cemitério, atendente, operacional e consulta/fiscalização, além de permissões por módulo.
  - Criações, edições, exclusões lógicas, anexos e operações cemiteriais registram usuário, data, operação e contexto.

- [x] **Dashboard operacional com dados reais**
  - Indicadores de falecidos, sepultamentos, sepulturas, ocupação, pendências, movimentações e manutenção são calculados do banco.
  - Últimos registros, alertas, pendências documentais e gráfico por período aparecem sem números fictícios.

- [x] **Falecidos, familiares e documentos**
  - Cadastro individual com dados pessoais, falecimento, sepultamento, busca tolerante a parte do nome/acentuação e prevenção de duplicidade.
  - Familiares/responsáveis podem se vincular a vários falecidos e manter histórico.
  - PDFs, JPG, JPEG e PNG podem ser anexados, visualizados/baixados com metadados e auditoria.

- [x] **Estrutura física, sepulturas e mapa**
  - Cadastro hierárquico de cemitério, quadra, rua, lote, sepultura, jazigo, catacumba, gaveta, ossuário e nicho.
  - Capacidade, vagas usadas/disponíveis e situações configuráveis são consistentes.
  - Mapa manual por quadra não inventa disposição: exibe somente unidades cadastradas, com status clicável e impressão.

- [x] **Sepultamentos e movimentações**
  - Sepultamento valida capacidade e evita ocupação simultânea; atualiza localização, status, histórico e protocolo.
  - Exumação, transferência e reinumação mantêm vínculo e histórico anterior, sem apagar registros.

- [x] **Atendimento, obras e manutenção**
  - Solicitações têm protocolo sequencial, anexos, tramitação e situação.
  - Reformas/construções percorrem recebida, análise, documentação, deferida/indeferida, execução e conclusão.
  - Patrimônio e ordens de serviço mantêm prioridade, prazo, situação e fotos.

- [x] **Financeiro configurável e documentos oficiais**
  - Serviços/taxas só são cobrados quando cadastrados e aprovados pela administração, com vigência, fundamento legal, isenção e histórico.
  - Modelos e emissões registram número, data, servidor, observações e cópia digital; não afirmam fé pública sem assinatura competente.

- [ ] **Relatórios, exportações, backup e proteção de dados**
  - Relatórios por período/situação/quadra/responsável exportam CSV/XLSX/PDF quando dependências estiverem disponíveis.
  - Backup manual/automático local inclui banco e documentos; restauração pede confirmação e cria cópia anterior.
  - Dados restritos não aparecem em consulta pública; exportações são autorizadas por perfil.

- [x] **Documentação e manutenção futura**
  - Manuais de instalação, administrador, usuário, backup/restauração e arquitetura acompanham o código.
  - O repositório contém instruções de atualização e estrutura compatível com PostgreSQL/empacotamento Windows.

- [x] **Validação funcional**
  - Fluxos de criar usuário/login/bloqueio, cadastrar/editar falecido, editar obras, solicitações, unidades físicas, familiares, manutenção, financeiro, usuários e metadados de documentos, anexar documento, cadastrar local, sepultar, movimentar, protocolar, emitir, relatar, exportar, fazer backup/restaurar e operar sem internet são verificados.

## Pendências deliberadas para etapa de implantação

- [ ] Execução agendada do backup automático, empacotamento instalável para Windows/Tauri e operação multiestação/sincronização online dependem da infraestrutura de implantação.
- [ ] QR Code interno para identificadores protegidos de sepulturas, protocolos e documentos pode ser adicionado sem expor dados pessoais.
