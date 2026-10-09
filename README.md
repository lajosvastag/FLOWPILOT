# FlowPilot

Plataforma de automação de processos para organizar tarefas repetitivas, acompanhar filas de execução e investigar falhas com histórico e logs.

A interface usa tema escuro azul-noturno, estética de painel web artesanal e identidade visual da Curie Edge. O usuário demonstrativo exibido na aplicação é Luís Brito.

## Recursos

- Dashboard com métricas de automações, execuções, sucesso e tempo economizado.
- Cadastro e edição de automações.
- Execução de fluxos por uma fila em segundo plano.
- Histórico com filtros por status e busca textual.
- Detalhes de cada execução, incluindo logs e mensagens de erro.
- Reexecução de tarefas que falharam.
- API JSON e banco SQLite criados automaticamente.
- Dados demonstrativos carregados na primeira execução.

## Requisitos

- Python 3.9 ou superior.
- Visual Studio Code com a extensão **Python** (recomendado para desenvolvimento).
- Nenhuma dependência externa de Python.

## Executar no VS Code

1. Clone o repositório:

   ```bash
   git clone https://github.com/lajosvastag/FLOWPILOT.git
   cd FLOWPILOT
   ```

2. Abra a pasta no VS Code:

   ```bash
   code .
   ```

3. Abra o terminal integrado em **Terminal > New Terminal**.

4. Inicie a aplicação:

   ```bash
   python3 app.py
   ```

   No Windows, use `python app.py` caso o comando `python3` não esteja disponível.

5. Acesse [http://localhost:3000](http://localhost:3000).

O banco local é criado em `data/flowpilot.db` na primeira execução. Esse arquivo é ignorado pelo Git.

## Usar outra porta

Linux e macOS:

```bash
PORT=8080 python3 app.py
```

Windows PowerShell:

```powershell
$env:PORT=8080; python app.py
```

## Verificar a API

Com a aplicação em execução:

```bash
curl http://localhost:3000/api/health
curl http://localhost:3000/api/summary
curl http://localhost:3000/api/automations
curl http://localhost:3000/api/executions
```

O endpoint de saúde deve retornar JSON com `"ok": true`.

## Executar com Docker

```bash
docker build -t flowpilot .
docker run --rm -p 3000:3000 flowpilot
```

Depois, abra [http://localhost:3000](http://localhost:3000).

## Estrutura

```text
app.py                  Servidor HTTP, API, SQLite e fila de tarefas
public/index.html       Estrutura da interface
public/styles.css       Estilos e tema visual
public/app.js           Navegação e integração com a API
public/curie-edge-logo.png
public/luis-brito-avatar.png
Dockerfile              Execução em container
```

## Autoria

Produto, identidade visual e tecnologia: **Curie Edge**.
