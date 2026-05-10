# 🏆 Copa 2026 Flag Generator

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> Gerador automatizado de PDFs das bandeiras da Copa do Mundo 2026. Baixa imagens via API FlagCDN.

## ✨ Funcionalidades

- 📥 Leitura automática de listas de países via Excel/CSV
- 🌐 Integração com API FlagCDN (alta resolução)
- 🎨 Geração de 2 PDFs: bandeiras coloridas e versão para colorir (contorno)
- 🧩 Arquitetura MVC em Python (modular, tipada e escalável)
- 📜 CLI completa com logs, timeout configurável e tratamento de erros

## 🚀 Instalação & Uso

```bash
# Clonar e instalar
git clone <seu-repo-url> && cd flag_generator
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Executar
python main.py --input classificados_copa_2026_OFICIAL.xlsx --output ./pdfs
```

## 📂 Estrutura

```bash
├── main.py          # Entry point (CLI)
├── controllers/     # Orquestração do fluxo
├── models/          # Lógica de dados e requisições API
├── views/           # Geração de PDFs e processamento de imagens
├── utils/           # Configurações e logging
└── config/          # Mapeamento escalável de códigos de países
```

## ⚙️ Opções da CLI

| Opção | Descrição | Padrão |
| :--- | :--- | :--- |
| `-i, --input` | **Obrigatório.** Arquivo Excel/CSV com coluna "País" | — |
| `-o, --output` | Diretório para salvar os PDFs gerados | `.` |
| `-c, --config` | Arquivo JSON com mapeamento personalizado de códigos | `config/country_codes.json` |
| `-t, --timeout` | Timeout das requisições HTTP (segundos) | `10` |
| `-l, --log-level` | Nível de logging: `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |

## 🤝 Contribuir

1 - Faça um Fork do projeto

2 - Crie uma branch (git checkout -b feat/nova-funcionalidade)

3 - Commit suas mudanças (git commit -m 'feat: adiciona suporte X')

4 - Push e abra um Pull Request

## 📧 Contato

email: pedropiva9@gmail.com
