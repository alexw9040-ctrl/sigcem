# Empacotamento Windows do SIGCEM

O projeto já contém a especificação PyInstaller e o script Inno Setup. O executável deve ser gerado em uma máquina Windows limpa, preferencialmente Windows 10/11 64 bits.

## Gerar a pasta executável

Instale Python 3.12+ e execute `installer\\build_windows.bat` a partir da pasta do projeto. O resultado será `dist\\SIGCEM\\SIGCEM.exe`.

## Gerar o instalador `.exe`

Instale o Inno Setup 6, abra `installer\\SIGCEM.iss` e clique em Compile. O instalador será criado em `installer\\output`.

O instalador cria atalhos para `start_sigcem.bat`. Esse lançador inicia o servidor local e abre `http://127.0.0.1:3000` no navegador. Na primeira execução, crie o administrador pelo formulário inicial.

## Dados e backup

O banco, documentos e backups ficam na pasta `data` ao lado do executável. Antes de uso oficial, configure cópias externas e teste a restauração.

## Validação obrigatória

O `.exe` final deve ser testado em Windows 10/11 sem Python instalado, com criação do primeiro administrador, cadastro, upload, emissão de PDF, backup/restauração e encerramento/reabertura do programa. O ambiente atual é Linux; por isso, a geração e a validação do binário Windows ainda são uma etapa de execução em Windows.
