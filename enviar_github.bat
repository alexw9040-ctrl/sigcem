@echo off
setlocal EnableExtensions
 title Envio do SIGCEM para o GitHub

 echo ================================================
 echo   SIGCEM - ENVIO DO PROJETO PARA O GITHUB
 echo ================================================
 echo.
 echo Este arquivo deve ser executado dentro da pasta extraida
 echo do pacote SIGCEM-GitHub-pronto.zip.
 echo.

 where git >nul 2>nul
 if errorlevel 1 (
   echo ERRO: o Git nao esta instalado ou nao esta no PATH.
   echo Instale o Git em: https://git-scm.com/download/win
   echo Depois feche e abra novamente este arquivo.
   pause
   exit /b 1
 )

 git --version
 echo.
 set /p REPO_URL=Cole a URL HTTPS do repositorio vazio do GitHub: 
 if "%REPO_URL%"=="" (
   echo ERRO: nenhuma URL foi informada.
   pause
   exit /b 1
 )

 echo.
 echo Conferindo os arquivos do projeto...
 if not exist app.py (
   echo ERRO: app.py nao foi encontrado.
   echo Execute este arquivo dentro da pasta que contem app.py.
   pause
   exit /b 1
 )
 if not exist requirements.txt (
   echo ERRO: requirements.txt nao foi encontrado.
   pause
   exit /b 1
 )

 if not exist .git (
   echo Inicializando o repositorio local...
   git init
   if errorlevel 1 goto :falha
 ) else (
   echo Repositorio local ja existente; sera reutilizado.
 )

 git branch -M main
 git remote get-url origin >nul 2>nul
 if errorlevel 1 (
   git remote add origin "%REPO_URL%"
 ) else (
   git remote set-url origin "%REPO_URL%"
 )

 echo.
 echo Preparando arquivos...
 git add .
 if errorlevel 1 goto :falha
 git diff --cached --quiet
 if errorlevel 1 (
   git commit -m "Adicionar projeto SIGCEM"
   if errorlevel 1 goto :falha
 ) else (
   echo Nenhuma alteracao nova para criar commit.
 )

 echo.
 echo Enviando para o GitHub...
 git push -u origin main
 if errorlevel 1 goto :falha

 echo.
 echo ================================================
 echo ENVIO CONCLUIDO COM SUCESSO!
 echo ================================================
 echo Abra no navegador o repositorio correspondente a:
 echo %REPO_URL%
 echo.
 pause
 exit /b 0

:falha
 echo.
 echo ================================================
 echo O envio nao foi concluido.
 echo ================================================
 echo.
 echo Verifique:
 echo 1. A URL deve ser parecida com https://github.com/SEU-USUARIO/sigcem.git
 echo 2. O repositorio deve existir e voce precisa ter permissao de escrita.
 echo 3. Se o GitHub pedir login, use sua conta ou um token pessoal.
 echo 4. Se aparecer "non-fast-forward", crie um repositorio realmente vazio,
 echo    sem README, sem .gitignore e sem licenca, e execute novamente.
 echo.
 pause
 exit /b 1
