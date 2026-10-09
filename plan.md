# FlowPilot — Plano de implementação

## Escopo
Plataforma de automação de processos para organizar tarefas repetitivas, processar dados e gerar relatórios. O produto terá uma dashboard navegável, criação/edição de automações, execução simulada com fila de tarefas, histórico de execuções e painel de erros detalhado.

## Arquitetura
- `app.py`: servidor HTTP Python 3 com API JSON, SQLite e fila em memória para execuções.
- `public/index.html`: shell da aplicação e marcação das áreas principais.
- `public/styles.css`: tema escuro roxo, responsividade e estados de interação.
- `public/app.js`: estado da interface, filtros, modais e consumo da API.
- `public/manus-routes.json`: manifesto da rota principal.
- `data/flowpilot.db`: criado automaticamente em runtime; não é versionado.

## Design
- **Movimento:** dark control room / neo-brutalismo refinado, com superfícies profundas e sinais de estado luminosos.
- **Princípios:** densidade informacional com respiro; hierarquia clara; ação sempre visível; feedback operacional em tempo real.
- **Cores:** azul elétrico como cor de ação e orientação; superfícies quase pretas, grafite azulado e separadores frios para dar profundidade sem abandonar o tema escuro; verde, âmbar e vermelho ficam reservados aos sinais semânticos de operação.
- **Layout:** navegação lateral persistente, cabeçalho contextual e canvas de operações sobre uma malha técnica azul-noturna, com blocos assimétricos, bordas duras, barras de título e leitura de site artesanal, evitando uma grade genérica centralizada.
- **Assinaturas:** marca hexagonal “F” em gradiente; linha de progresso violeta; cartões com trilha lateral de status.
- **Interação:** cada clique importante responde com mudança de status, toast e registro no histórico. Modais curtos para decisões, sem esconder contexto.
- **Animação:** entrada suave de cards, pulse discreto em automações ativas e transições de 180–240ms; nenhum movimento decorativo excessivo.
- **Tipografia:** Inter/system para interface, com pesos 500/600/700; números operacionais em fonte monoespaçada.
- **Essência:** “o painel de controle para fazer o trabalho repetitivo desaparecer”; confiável, direto, vigilante. A autoria visual e tecnológica exibida no produto é da Curie Edge.
- **Voz:** objetiva e encorajadora. Exemplos: “Automatize o próximo gargalo.” e “Cada execução deixa um rastro claro.”
- **Logotipo:** monograma F formado por dois trilhos conectados dentro de um hexágono arredondado.
- **Cor proprietária:** `#8B5CF6` (violeta FlowPilot).

## Comportamentos essenciais
1. Dashboard com métricas de automações, execuções, taxa de sucesso e tempo economizado.
2. Lista de automações com busca/filtro por status e ação de executar.
3. Execução cria registro, passa por fila e pode terminar com sucesso ou erro demonstrativo.
4. Histórico com filtros de período/status e detalhe expansível de cada execução.
5. Página de detalhes de erro com etapa, mensagem e payload.
6. Modal para nova automação e persistência via SQLite.
7. Navegação entre Visão geral, Automações, Execuções e Configurações sem recarregar a página.

## Execução
Aplicação sem dependências externas: `python3 app.py`, escutando em `0.0.0.0:3000` ou na porta de `PORT`. O banco SQLite é criado automaticamente e a interface recebe dados seed na primeira execução.
