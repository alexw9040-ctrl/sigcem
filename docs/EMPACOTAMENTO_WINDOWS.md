# Empacotamento Windows do SIGCEM

O projeto já contém a especificação PyInstaller e o script Inno Setup. O executável deve ser gerado em uma máquina Windows limpa, preferencialmente Windows 10/11 64 bits.

## Gerar a pasta executável

Instale Python 3.12+ e execute `installer\\build_windows.bat` a partir da pasta do projeto. O resultado será `dist\\SIGCEM\\SIGCEM.exe`.

## Gerar o instalador `.exe`

Instale o Inno Setup 6, abra `installer\\SIGCEM.iss` e clique em Compile. O instalador será criado em `installer\\output`.

O instalador cria atalhos para `start_sigcem.bat`. Esse lançador inicia o servidor local e abre `http://127.0.0.1:3000` no navegador. Na primeira execução, crie o administrador pelo formulário inicial.

## Compilação automática pelo GitHub Actions

O arquivo `.github/workflows/build-windows.yml` compila o executável e o instalador automaticamente em um ambiente Windows do GitHub. No repositório, abra a aba **Actions**, selecione **Compilar instalador Windows**, clique em **Run workflow** e aguarde a conclusão. Ao finalizar, baixe os artefatos `SIGCEM-Setup-Windows` e `SIGCEM-Windows-portatil` na página da execução.

Esse processo gera um instalador `.exe` mesmo quando o computador usado para editar o projeto não possui Windows. A compilação não inclui banco, documentos ou dados reais; esses dados são criados localmente no PC onde o SIGCEM for instalado.

## Dados e backup

O banco, documentos e backups ficam na pasta `data` ao lado do executável. Antes de uso oficial, configure cópias externas e teste a restauração.

## Validação obrigatória

O `.exe` final deve ser testado em Windows 10/11 sem Python instalado, com criação do primeiro administrador, cadastro, upload, emissão de PDF, backup/restauração e encerramento/reabertura do programa. O ambiente atual é Linux; por isso, a geração e a validação do binário Windows ainda são uma etapa de execução em Windows.
