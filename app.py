import json
import random
import os
from flask import Flask, request, jsonify, render_template_string
# Tenta importar o SDK do Mercado Pago.
# Se falhar, a aplicação irá mostrar um erro útil.
try:
    import mercadopago
except ImportError:
    mercadopago = None

# --- Configurações Iniciais ---
ARQUIVO_DADOS = 'torneio_lol_data.json'

# --- Configure o Mercado Pago SDK com seu access token ---
# IMPORTANTE: Substitua "SEU_ACCESS_TOKEN_AQUI" pelo seu token real.
# Você pode obter um token de teste ou de produção no painel do Mercado Pago.
if mercadopago:
    sdk = mercadopago.SDK("APP_USR-4028934087122957-091918-25cc9b5921a9c1b767605e28b3d44e48-188258998")

app = Flask(__name__)

# --- Funções de Armazenamento do Torneio (Refatoradas para Web) ---
def salvar_torneio(torneio):
    """Salva os dados do torneio em um arquivo JSON."""
    with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as f:
        json.dump(torneio, f, indent=4)
    return True

def carregar_torneio():
    """Carrega os dados do torneio a partir de um arquivo JSON."""
    if os.path.exists(ARQUIVO_DADOS):
        with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def criar_novo_torneio(nome):
    """Cria um novo torneio com o nome fornecido."""
    torneio = {
        "nome": nome,
        "jogadores": [],
        "partidas": [],
        "premios": {},
        "rodada_atual": 0
    }
    salvar_torneio(torneio)
    return torneio

# --- Lógica do Torneio (Refatorada para ser chamada por rotas) ---
def adicionar_jogador_internamente(torneio, nome_jogador):
    """Adiciona um jogador ao torneio."""
    if nome_jogador not in torneio["jogadores"]:
        torneio["jogadores"].append(nome_jogador)
        torneio["premios"][nome_jogador] = 0
        salvar_torneio(torneio)
        return True
    return False

def gerar_chaveamento_internamente(torneio):
    """Gera os confrontos da próxima rodada."""
    jogadores_ativos = torneio["jogadores_ativos"] if "jogadores_ativos" in torneio and torneio["rodada_atual"] > 0 else torneio["jogadores"]
    
    if len(jogadores_ativos) < 2 and torneio["rodada_atual"] == 0:
        return {"status": "erro", "mensagem": "É necessário no mínimo 2 jogadores para iniciar uma rodada."}
    if len(jogadores_ativos) <= 1 and torneio["rodada_atual"] > 0:
        campeao = jogadores_ativos[0] if jogadores_ativos else "Nenhum"
        return {"status": "erro", "mensagem": f"O torneio já terminou! O campeão é: {campeao}"}

    random.shuffle(jogadores_ativos)
    partidas = []
    i = 0
    while i < len(jogadores_ativos):
        if i + 1 < len(jogadores_ativos):
            partidas.append({"jogador1": jogadores_ativos[i], "jogador2": jogadores_ativos[i+1]})
            i += 2
        else:
            partidas.append({"jogador1": jogadores_ativos[i], "jogador2": "BYE"})
            i += 1
    
    torneio["partidas"] = partidas
    torneio["rodada_atual"] += 1
    torneio["jogadores_ativos"] = []
    salvar_torneio(torneio)
    return {"status": "sucesso", "mensagem": "Chaveamento gerado com sucesso!"}

def registrar_vencedor_internamente(torneio, vencedor, premio):
    """Registra o vencedor de uma partida."""
    # Encontra o jogador na lista de jogadores ativos para evitar duplicação
    if vencedor not in torneio["premios"]:
        return {"status": "erro", "mensagem": "Vencedor não é um jogador válido."}

    torneio["premios"][vencedor] += premio
    
    # Remove a partida da lista de pendentes e adiciona o vencedor à lista de ativos
    encontrado = False
    partidas_atualizadas = []
    for partida in torneio["partidas"]:
        if partida["jogador1"] == vencedor or partida["jogador2"] == vencedor:
            # Encontrou a partida, não a adiciona na lista atualizada
            if "jogadores_ativos" not in torneio:
                torneio["jogadores_ativos"] = []
            torneio["jogadores_ativos"].append(vencedor)
            encontrado = True
        else:
            partidas_atualizadas.append(partida)

    torneio["partidas"] = partidas_atualizadas
    
    if not encontrado:
        return {"status": "erro", "mensagem": "Jogador não encontrado nas partidas atuais."}
    
    salvar_torneio(torneio)
    return {"status": "sucesso", "mensagem": f"Vencedor '{vencedor}' e prêmio de R${premio:.2f} registrados!"}


# --- Rotas do Flask ---
@app.route('/')
def index():
    torneio = carregar_torneio() or {"nome": "Nenhum torneio ativo", "jogadores": [], "partidas": [], "premios": {}, "rodada_atual": 0}
    
    html_template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>Gerenciador de Torneio LoL</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #f0f2f5; color: #333; margin: 0; padding: 20px; }
            .container { max-width: 800px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
            h1, h2, h3 { color: #007bff; }
            .section { margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 6px; }
            .btn { padding: 10px 15px; border: none; border-radius: 4px; color: white; cursor: pointer; }
            .btn-primary { background-color: #007bff; }
            .btn-success { background-color: #28a745; }
            .btn-danger { background-color: #dc3545; }
            input[type="text"], input[type="email"], input[type="number"] { width: 100%; padding: 8px; margin: 8px 0; box-sizing: border-box; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Gerenciador de Torneio LoL</h1>
            <h2>Torneio Atual: {{ torneio.nome }}</h2>
    
            <!-- Seção de Gerenciamento do Torneio -->
            <div class="section">
                <h3>Gerenciar Torneio</h3>
                <form action="/criar-torneio" method="post" onsubmit="return handleFormSubmit(this, 'torneio-msg');">
                    <input type="text" name="nome" placeholder="Novo nome do torneio" required>
                    <button type="submit" class="btn btn-danger">Resetar/Criar Torneio</button>
                </form>
                <div id="torneio-msg"></div>
            </div>
    
            <!-- Seção de Jogadores -->
            <div class="section">
                <h3>Jogadores</h3>
                <form action="/adicionar-jogador" method="post" onsubmit="return handleFormSubmit(this, 'jogador-msg');">
                    <input type="text" name="nome_jogador" placeholder="Nome do Jogador" required>
                    <input type="email" name="email" placeholder="Email para pagamento" required>
                    <input type="number" name="valor" placeholder="Valor da inscrição (ex: 50.0)" step="0.01" required>
                    <button type="submit" class="btn btn-primary">Adicionar e Pagar</button>
                </form>
                <div id="jogador-msg"></div>
                <h4>Jogadores Inscritos ({{ torneio.jogadores | length }})</h4>
                <ul>
                    {% for jogador in torneio.jogadores %}
                    <li>{{ jogador }}</li>
                    {% endfor %}
                </ul>
            </div>
    
            <!-- Seção de Partidas -->
            <div class="section">
                <h3>Partidas e Resultados</h3>
                <form action="/gerar-chaveamento" method="post" onsubmit="return handleFormSubmit(this, 'chaveamento-msg');">
                    <button type="submit" class="btn btn-primary">Gerar Próxima Rodada</button>
                </form>
                <div id="chaveamento-msg"></div>
                <h4>Partidas Atuais (Rodada {{ torneio.rodada_atual }})</h4>
                <ul>
                    {% for partida in torneio.partidas %}
                    <li>{{ partida.jogador1 }} vs {{ partida.jogador2 }}</li>
                    {% endfor %}
                </ul>
            </div>

            <!-- Seção de Registro de Vencedores -->
            <div class="section">
                <h3>Registrar Vencedor</h3>
                <form action="/registrar-vencedor" method="post" onsubmit="return handleFormSubmit(this, 'vencedor-msg');">
                    <input type="text" name="vencedor" placeholder="Nome do vencedor" required>
                    <input type="number" name="premio" placeholder="Prêmio da partida (ex: 100.0)" step="0.01" required>
                    <button type="submit" class="btn btn-success">Registrar Vencedor</button>
                </form>
                <div id="vencedor-msg"></div>
            </div>

            <!-- Seção de Prêmios -->
            <div class="section">
                <h3>Ranking de Prêmios</h3>
                <ul>
                    {% for jogador, premio in torneio.premios.items() %}
                    <li>{{ jogador }}: R${{ "%.2f" | format(premio) }}</li>
                    {% endfor %}
                </ul>
            </div>
        </div>
        <script>
            async function handleFormSubmit(form, messageElementId) {
                event.preventDefault();
                const formData = new FormData(form);
                const data = Object.fromEntries(formData.entries());
    
                const response = await fetch(form.action, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
    
                const result = await response.json();
                const messageDiv = document.getElementById(messageElementId);
                messageDiv.textContent = result.mensagem || result.message;
                messageDiv.style.color = result.status === 'sucesso' ? 'green' : 'red';
                
                if (result.status === 'sucesso') {
                    // Atualiza a página após um pequeno delay para mostrar as mudanças
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                }
    
                // Verifica a resposta de pagamento e exibe o QR Code
                if (result.id) {
                    messageDiv.innerHTML += `<br>ID do pagamento: ${result.id}`;
                    if (result.point_of_interaction && result.point_of_interaction.transaction_data && result.point_of_interaction.transaction_data.qr_code_base64) {
                        messageDiv.innerHTML += `<br>QR Code para PIX: <br><img src="data:image/png;base64,${result.point_of_interaction.transaction_data.qr_code_base64}" alt="QR Code" style="width:150px; height:150px;">`;
                    }
                }
    
                return false;
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template, torneio=torneio)

@app.route('/criar-torneio', methods=['POST'])
def criar_torneio_route():
    dados = request.json
    nome = dados.get("nome", "Novo Torneio")
    criar_novo_torneio(nome)
    return jsonify({"status": "sucesso", "mensagem": f"Torneio '{nome}' criado com sucesso!"})

@app.route('/adicionar-jogador', methods=['POST'])
def adicionar_jogador_route():
    dados = request.json
    nome_jogador = dados.get("nome_jogador")
    email = dados.get("email")
    valor = dados.get("valor")

    if not nome_jogador or not email or not valor:
        return jsonify({"status": "erro", "mensagem": "Dados de jogador, email ou valor faltando."})

    torneio = carregar_torneio()
    if not torneio:
        return jsonify({"status": "erro", "mensagem": "Nenhum torneio ativo. Crie um primeiro."})
    
    if not mercadopago:
        return jsonify({"status": "erro", "mensagem": "A biblioteca do Mercado Pago não foi encontrada. Instale com 'pip install mercadopago'."})

    try:
        # Tenta criar o pagamento com o Mercado Pago
        pagamento_data = {
            "transaction_amount": float(valor),
            "description": f"Inscrição Campeonato LoL - {nome_jogador}",
            "payment_method_id": "pix",
            "payer": {
                "email": email
            }
        }
        pagamento_response = sdk.payment().create(pagamento_data)
        
        if pagamento_response["status"] == 201:
            # Se o pagamento foi criado com sucesso, adiciona o jogador
            adicionar_jogador_internamente(torneio, nome_jogador)
            response_data = {
                "status": "sucesso",
                "mensagem": f"Pagamento criado para {nome_jogador}. Aguardando a aprovação. Player adicionado ao torneio.",
                "id": pagamento_response['response']['id']
            }
            if 'point_of_interaction' in pagamento_response['response']:
                response_data['point_of_interaction'] = pagamento_response['response']['point_of_interaction']

            return jsonify(response_data)
        else:
            return jsonify({"status": "erro", "mensagem": f"Erro ao criar pagamento: {pagamento_response['response']['message']}"})

    except Exception as e:
        return jsonify({"status": "erro", "mensagem": f"Ocorreu um erro no pagamento: {str(e)}. Verifique se o seu Access Token está correto."})

@app.route('/gerar-chaveamento', methods=['POST'])
def gerar_chaveamento_route():
    torneio = carregar_torneio()
    if not torneio:
        return jsonify({"status": "erro", "mensagem": "Nenhum torneio ativo. Crie um primeiro."})
    
    return jsonify(gerar_chaveamento_internamente(torneio))

@app.route('/registrar-vencedor', methods=['POST'])
def registrar_vencedor_route():
    dados = request.json
    vencedor = dados.get("vencedor")
    premio = dados.get("premio")

    if not vencedor or premio is None:
        return jsonify({"status": "erro", "mensagem": "Nome do vencedor ou prêmio faltando."})

    torneio = carregar_torneio()
    if not torneio:
        return jsonify({"status": "erro", "mensagem": "Nenhum torneio ativo. Crie um primeiro."})
    
    return jsonify(registrar_vencedor_internamente(torneio, vencedor, float(premio)))

# --- Bloco de execução ---
if __name__ == '__main__':
    # Bloco para tratar erros na inicialização do servidor.
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print("\n---------------- ERRO AO INICIAR O SERVIDOR ----------------")
        print("Causa do erro:", e)
        print("\nSolução provável:")
        print("- Verifique se você instalou as bibliotecas Flask e mercadopago.")
        print("  Use o comando no terminal: pip install Flask mercadopago")
        print("- Certifique-se de que o VS Code está usando a versão do Python")
        print("  onde as bibliotecas foram instaladas.")
        print("------------------------------------------------------------\n")