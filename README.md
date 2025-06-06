# 🚇 LisbonMetroAPI-Wrapper-MCP-Server

## 🔐 Autenticação API Metro Lisboa

1. **Aceder ao url: https://api.metrolisboa.pt/store/**

2. **Criar Conta**

3. **Na aba "Applications" criar uma nova aplicação**

4. **Aceder à aba "APIS" selecionar "EstadoServicoML - 1.0.1"**

5. **Selecionar a aplicação criada e subscrever a API**

6. **Guardar o URL exibido na secção "Production and Sandbox Endpoints"**

7. **Carregar na aba "API Console", selecionar:**

    Try - APPLICATION_NAME
    Using - Production

    Com estas opções será exibido o TOKEN de acesso à API



## ⚙️ Instruções para correr o projeto via Smithery

1. **Aceder ao URL do MCP Server**
    https://smithery.ai/server/@PedroCorreiaaa/lisbonmetroapi-wrapper-mcp-server
    
2. **Instalar**
    1. Na aba "Install" selecionar Claude Desktop
    2. Preencher os campos "metroApiBase" e "metroApiToken", carregar em Connect
    3. Correr no terminal o comando que foi gerado
    4. Abrir o Claude e testar
    
## 💻 Instruções para correr o projeto localmente

1. **Clonar o repositório** (se ainda não tiveres feito):
   ```bash
   git clone https://github.com/PedroCorreiaaa/LisbonMetroAPI-Wrapper-MCP-Server
   cd LisbonMetroAPI-Wrapper-MCP-Server
2. **Ativar Ambiente Virtual**
    ```
    .venv\Scripts\activate
3. **Instalar Requirements**
    ```
    pip install requirements.txt
4. **Configurar .env**
    ```
    METRO_API_TOKEN=<METRO_API_TOKEN>
    ```
5. **Aceder à configuração do Claude Desktop**
    ```
    code $env:AppData\Claude\claude_desktop_config.json
6. **Alterar configuração do Claude Desktop**
    ```
    {
        "mcpServers": {
            "metro-lisboa": {
            "command": "PATH_TO_LOCAL_REPO/.venv/Scripts/python.exe",
            "args": [
                "PATH_TO_LOCAL_REPO/metro-lisboa.py"
            ]
            }
        }
    }
7. **Correr o projeto**
    ```bash
    python metro-lisboa.py
8. **Testar no Claude Desktop**
    ```
    Ex: Quero ir de metro do estádio da luz até à altice arena, qual a melhor rota?