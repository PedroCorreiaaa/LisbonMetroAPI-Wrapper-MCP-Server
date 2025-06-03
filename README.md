# LisbonMetroAPI-Wrapper-MCP-Server



## Instruções para correr o projeto

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
4. **Aceder à configuração do Claude Desktop**
    ```
    code $env:AppData\Claude\claude_desktop_config.json
5. **Alterar configuração do Claude Desktop**
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
6. **Correr o projeto**
    ```bash
    python metro-lisboa.py
7. **Testar no Claude Desktop**
    ```
    Ex: Quero ir de metro do estádio da luz até à altice arena, qual a melhor rota?