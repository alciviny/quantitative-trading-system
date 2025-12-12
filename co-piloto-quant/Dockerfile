# Use uma imagem base Python leve
FROM python:3.10-slim-buster

# Define o diretório de trabalho dentro do container
WORKDIR /app/co-piloto-quant

# Instala dependências de sistema necessárias (ex: para compilação de pacotes Python)
# build-essential inclui gcc, g++ e make, que são frequentemente necessários
# para compilar certas bibliotecas Python com extensões C.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copia apenas os arquivos de configuração de dependências
COPY pyproject.toml poetry.lock ./

# Instala o Poetry
RUN pip install poetry

# Instala as dependências do projeto de produção (sem o próprio projeto por enquanto)
# Isso permite que a camada seja cacheada se apenas o código-fonte mudar, mas as dependências não.
RUN poetry install --no-root --only main

# Copia o restante do código fonte
COPY . .

# Instala o próprio projeto no ambiente do container
# poetry install --no-dev instala o projeto e suas dependências de produção (já instaladas acima)
RUN poetry install --no-dev

# Expõe uma porta se o seu bot tiver alguma interface web ou API (não especificado, mas boa prática)
# EXPOSE 8000 

# Comando para rodar o bot
# Assume que run_live_bot.py está em scripts/ dentro do diretório do projeto
# e que você quer rodá-lo com python.
# As variáveis de ambiente devem ser passadas via docker run -e ou docker-compose
CMD ["python", "scripts/run_live_bot.py"]
