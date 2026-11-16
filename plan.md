# SIGCEM — plano de implementação

## Escopo aprovado
Construir um sistema real de gestão de cemitério municipal para Ararendá–CE, conforme o Prompt Master em PDF. A primeira entrega deve ser executável localmente, sem internet, e já conter banco SQLite, autenticação, permissões, cadastros, operações cemiteriais, documentos, auditoria, backup e interface responsiva. A arquitetura será preparada para PostgreSQL/rede local e empacotamento Windows posteriormente.

## Arquitetura e implementação
- Backend Python 3.12 + Flask, com SQLite local em `data/sigcem.db`, uploads e backups em `data/`.
- SQL relacional com chaves estrangeiras, transações para sepultamentos e exclusão lógica para preservar histórico.
- Sessão local com hash de senha Werkzeug; primeiro acesso cria o administrador sem senha padrão permanente.
- Frontend server-rendered em Jinja, HTML sem dependências externas obrigatórias, CSS responsivo e JavaScript mínimo para busca, navegação, confirmação e gráficos.
- Exportação CSV/XLSX/PDF usando bibliotecas locais quando disponíveis; impressão via CSS e navegador quando necessário.
- Modelo de dados modular: usuários/perfis, falecidos, familiares, estrutura física, sepultamentos/movimentações, solicitações, obras, manutenção, serviços/taxas, documentos, auditoria, backups e configurações.
- Serviço local escuta em `0.0.0.0:3000` para Preview e também pode ser executado em `127.0.0.1` em uma estação sem internet.
- `public/manus-routes.json` declara a rota principal para o Preview; a aplicação possui rotas internas de módulos.

## Design

### Alternativas consideradas
- **Arquivo público contemporâneo** (0,08): institucional, sereno e orientado a busca, com azul-petróleo e areia.
- **Painel cívico modular** (0,07): alto contraste, densidade informacional e foco operacional.
- **Cartografia silenciosa** (0,06): linguagem de mapa, linhas finas e estados cromáticos.

### Escolha: Painel cívico modular
**Movimento:** civic tech editorial, com a clareza de um sistema público contemporâneo e a precisão visual de uma central de operações.

**Princípios:** clareza antes de decoração; ações primárias evidentes; status sempre codificados por texto e cor; densidade confortável para uso diário.

**Cores:** fundo marfim muito claro; azul-marinho para autoridade; azul-petróleo como cor proprietária de ação; verde, âmbar e vermelho somente para estados; cinza-azulado para estrutura.

**Layout:** shell de navegação lateral recolhível + área de trabalho larga; páginas de módulo usam cabeçalho de contexto, filtros e tabelas; detalhes abrem em cartões e trilhas de histórico, evitando telas soltas.

**Assinaturas:** marca SIGCEM desenhada como monograma de mapa/sepultura; chips de situação; linha vertical de auditoria e timeline de movimentações.

**Interação:** cada ação destrutiva pede confirmação e explica a preservação histórica; formulários são divididos por seções; busca global fica sempre acessível; feedback aparece próximo da ação.

**Animação:** transições de 160–220ms, entrada suave de cartões e barras de progresso; nenhum movimento contínuo ou ornamental que distraia durante atendimento.

**Tipografia:** Inter para interface e títulos; fallback system sans-serif para operação offline. Hierarquia por peso e espaçamento, não por excesso de tamanhos.

**Essência da marca:** “A memória do município, organizada para o trabalho de todos os dias.” Personalidade: confiável, humana, precisa.

**Voz:** direta, respeitosa e operacional. Exemplos: “Encontre o registro certo antes de abrir um novo.” / “Toda alteração fica registrada no histórico.”

**Marca:** wordmark SIGCEM com o “G” sugerindo um caminho cartográfico em negativo; ícone formado por uma quadra, um ponto e uma linha de localização.

**Cor proprietária:** azul-petróleo `#0E5A63`.

## Estrutura de pastas
- `app.py`: servidor Flask, rotas, regras transacionais e inicialização SQLite.
- `templates/`: layout, login/setup, dashboard e telas dos módulos.
- `static/`: CSS e JavaScript locais.
- `data/`: banco, uploads e backups (gerado em runtime, não versionar dados reais).
- `public/manus-routes.json`: manifesto de rotas.
- `requirements.txt`: dependências locais e de empacotamento.
- `docs/`: manuais operacionais e técnicos.
- `app.config.ts`: metadado de marca do projeto.

## Sequência de entrega
1. Fundação: layout, login, criação de administrador, banco, permissões e auditoria.
2. Núcleo cemiterial: falecidos, familiares, estrutura, sepulturas e sepultamentos.
3. Operações: mapa manual, exumações, transferências, reinumações, solicitações, reformas e manutenção.
4. Administração: documentos, taxas configuráveis, relatórios, exportações, backups e configurações.
5. Validação: lint/compile, fluxos HTTP, regras de capacidade, auditoria, backup e modo sem internet.
6. Entrega: documentação, checkpoint Git e orientação para empacotamento Windows.

## Limites conscientes
A instalação nativa Windows/Tauri e a sincronização multiestação exigem uma etapa específica de empacotamento e testes no Windows. O código será desenvolvido local-first e sem dependência de serviço pago; o Preview serve para validação da aplicação enquanto o pacote desktop é preparado.
