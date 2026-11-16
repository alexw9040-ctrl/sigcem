# SIGCEM — Sistema Integrado de Gestão de Cemitério Municipal

Este pacote contém o projeto completo do SIGCEM, desenvolvido para gestão de cemitérios municipais.

## Publicar no GitHub — método recomendado

O arquivo ZIP deve ser **extraído primeiro**. Não envie o ZIP como um único arquivo se quiser que o GitHub mostre o código do sistema.

1. No GitHub, crie um repositório novo chamado, por exemplo, `sigcem`.
2. Na criação, deixe o repositório vazio: não marque README, `.gitignore` ou licença.
3. Extraia este ZIP para uma pasta no computador.
4. Abra a pasta extraída e execute o arquivo `enviar_github.bat`.
5. Cole a URL HTTPS do repositório, por exemplo `https://github.com/SEU-USUARIO/sigcem.git`.
6. Quando o GitHub solicitar autenticação, entre na sua conta. Se solicitar senha no terminal, use um token pessoal do GitHub, não a senha comum da conta.

O arquivo `.bat` inicializa o Git, cria o branch `main`, configura o endereço remoto, cria o commit e envia todos os arquivos. Ele também informa os erros mais comuns.

## Método manual pelo Prompt de Comando

Se preferir fazer manualmente, abra o Prompt de Comando dentro da pasta que contém `app.py`:

```bat
git init
git add .
git commit -m "Adicionar projeto SIGCEM"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/sigcem.git
git push -u origin main
```

### Erros comuns no envio

- **Repository not found**: a URL está incorreta, o repositório não foi criado ou sua conta não tem permissão.
- **Authentication failed**: o GitHub exige autenticação por navegador, GitHub CLI ou token pessoal; a senha normal geralmente não funciona.
- **non-fast-forward**: o repositório não está vazio. Crie outro repositório vazio ou remova o README criado automaticamente antes do primeiro envio.
- **O GitHub mostra apenas um ZIP**: o ZIP foi enviado sem ser extraído. Baixe o pacote novamente, extraia-o e envie o conteúdo da pasta.

## Execução local no Windows

Instale Python 3.12 ou superior e execute `installer\\build_windows.bat` para gerar o executável. O instalador Inno Setup está em `installer\\SIGCEM.iss`.

## Dados

O banco, uploads e backups são criados na pasta `data` durante a execução. O pacote não contém dados reais nem dados de teste.

## Aviso

Antes de usar em produção, configure segredo de sessão, usuários individuais, backups externos, HTTPS, política LGPD e as regras municipais. Consulte também `docs/INSTALACAO.md`, `docs/EMPACOTAMENTO_WINDOWS.md` e `docs/HOSPEDAGEM_EXTERNA.md`.
