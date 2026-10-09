# FlowPilot — Plataforma de automação de processos

Dashboard operacional em tema escuro roxo para organizar automações, acompanhar filas e investigar falhas.

## Requisitos

- Python 3.9 ou superior
- Nenhuma dependência externa

## Executar

```bash
python3 app.py
```

Abra `http://localhost:3000` no navegador. Para usar outra porta:

```bash
PORT=8080 python3 app.py
```

## O que está incluído

A aplicação usa Python com `ThreadingHTTPServer`, API JSON, SQLite e uma fila de tarefas em memória. O arquivo `data/flowpilot.db` é criado automaticamente na primeira execução e recebe dados demonstrativos para a dashboard já iniciar preenchida.

Na interface é possível criar automações, executar fluxos, acompanhar a execução em andamento, filtrar o histórico e abrir detalhes de erros com logs e opção de reexecução.

## Autoria

A identidade visual, o produto e a tecnologia desta plataforma são apresentados como autoria integral da **Curie Edge**, conforme solicitado.
