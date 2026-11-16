# Hospedagem externa do SIGCEM

O SIGCEM é uma aplicação Flask com arquivos locais para SQLite, uploads e backups. Para colocá-lo fora da Manus, há três caminhos principais.

## Recomendação para a Prefeitura

A opção mais controlável é um VPS Linux próprio ou contratado, usando Docker, HTTPS com domínio municipal e backup externo. O Dockerfile já está no projeto. Em produção, o Flask deve ser executado por um servidor WSGI como Gunicorn, atrás de um proxy HTTPS como Nginx. A documentação oficial do Flask explica que o servidor de desenvolvimento não deve ser usado em produção e apresenta WSGI, Gunicorn e proxy reverso: https://flask.palletsprojects.com/en/stable/deploying/.

Para vários servidores e usuários simultâneos, recomenda-se substituir SQLite por PostgreSQL e armazenar documentos em volume persistente ou armazenamento de objetos. O SQLite atual é adequado ao modo local/offline e a uma instalação municipal pequena em servidor único, mas não deve ser compartilhado diretamente por vários computadores em uma pasta de rede.

## Plataformas gerenciadas

Render, Railway, Fly.io, Google Cloud Run, Azure App Service e AWS podem executar o container. A configuração deve incluir banco persistente, armazenamento persistente para `data/` ou armazenamento de objetos, domínio, HTTPS, backups e variáveis secretas. O Render informa que o filesystem padrão é efêmero e que um Persistent Disk é necessário para preservar alterações entre deploys e reinicializações: https://render.com/docs/disks.

Uma VPS com Docker é mais simples para o SIGCEM porque mantém controle sobre o SQLite, uploads e backups. A DigitalOcean mantém um roteiro oficial de Flask com Docker e VPS: https://www.digitalocean.com/community/tutorial-collections/how-to-build-and-deploy-a-flask-application-using-docker.

## Não recomendado

Hospedagem compartilhada tradicional, hospedagem apenas de arquivos HTML e serviços sem volume persistente não são adequados. Eles podem até exibir a interface, mas não garantem execução do Flask, preservação do banco, documentos e backups.

## Dados mínimos para uma implantação oficial

Use domínio próprio, HTTPS, segredo de sessão alterado, usuários individuais, firewall, backups automáticos fora do servidor, teste de restauração, monitoramento, política LGPD e responsável técnico. A versão publicada na Manus e qualquer container com filesystem efêmero devem ser tratados apenas como ambiente temporário até que a persistência seja configurada.
