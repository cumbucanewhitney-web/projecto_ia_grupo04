"""
buscas.py
Implementação dos sete algoritmos de pesquisa:
1. BFS (teste de objectivo na geração)
2. DFS (controlo de ciclos no caminho + limite de profundidade configurável)
3. IDS (reporta nós re-expandidos)
4. UCS (fila de prioridade heapq)
5. Gulosa
6. A*
7. DFBnB
"""

from collections import deque
from dataclasses import dataclass
from itertools import count
from time import perf_counter
import heapq
import tracemalloc

from problema import No


@dataclass
class ResultadoBusca:
    """Resultado e métricas de uma execução."""

    algoritmo: str
    estado_solucao: object = None
    acoes_solucao: list = None
    estados_solucao: list = None

    custo_solucao: float = float("inf")
    comprimento_caminho: int = 0

    nos_expandidos: int = 0
    nos_gerados: int = 0
    nos_reexpandidos: int = 0
    tamanho_maximo_fronteira: int = 0

    tempo_segundos: float = 0.0
    memoria_pico_mb: float = 0.0

    sucesso: bool = False
    motivo: str = ""

    def __post_init__(self):
        if self.acoes_solucao is None:
            self.acoes_solucao = []
        if self.estados_solucao is None:
            self.estados_solucao = []


def _construir_no_inicial(problema, estado_inicial=None):
    if estado_inicial is None:
        estado_inicial = problema.estado_inicial()
    return No(estado=estado_inicial, pai=None, acao=None, custo=0.0, profundidade=0)


def _construir_caminho(no):
    nos = no.caminho_nos()
    estados = [n.estado for n in nos]
    acoes = [n.acao for n in nos[1:]]
    return estados, acoes


def _preencher_resultado_sucesso(resultado, no_solucao):
    estados, acoes = _construir_caminho(no_solucao)
    resultado.estado_solucao = no_solucao.estado
    resultado.estados_solucao = estados
    resultado.acoes_solucao = acoes
    resultado.custo_solucao = no_solucao.custo
    resultado.comprimento_caminho = no_solucao.profundidade
    resultado.sucesso = True
    resultado.motivo = "Solução encontrada."
    return resultado


def _executar_com_metricas(nome, funcao):
    """
    Executa a pesquisa medindo tempo e memória.
    As métricas parciais são guardadas no próprio `resultado` antes de
    qualquer TimeoutError ou MemoryError para nunca perder os contadores.
    """
    resultado = ResultadoBusca(algoritmo=nome, motivo="Não foi encontrada uma solução.")
    tracemalloc.start()
    inicio = perf_counter()

    try:
        funcao(resultado, inicio)
    except TimeoutError:
        resultado.sucesso = False
        resultado.motivo = "Limite de tempo excedido."
    except MemoryError:
        resultado.sucesso = False
        resultado.motivo = "Memória insuficiente."
    finally:
        tempo = perf_counter() - inicio
        _, memoria_pico = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    resultado.tempo_segundos = tempo
    resultado.memoria_pico_mb = memoria_pico / (1024 * 1024)
    return resultado


def _verificar_limites(inicio, limite_segundos, nos_expandidos, limite_expansoes):
    if limite_segundos is not None and perf_counter() - inicio >= limite_segundos:
        raise TimeoutError()
    if limite_expansoes is not None and nos_expandidos >= limite_expansoes:
        raise TimeoutError()


def _chave(problema, estado):
    return problema.chave_estado(estado)


def _gerar_filhos(problema, no, inicio=None, limite_segundos=None):
    filhos = []
    for idx, acao in enumerate(problema.acoes(no.estado)):
        if inicio is not None and limite_segundos is not None and (idx & 63) == 0:
            if perf_counter() - inicio >= limite_segundos:
                raise TimeoutError()

        novo_estado = problema.resultado(no.estado, acao)
        custo_transicao = problema.custo(no.estado, acao, novo_estado)
        filhos.append(
            No(
                estado=novo_estado,
                pai=no,
                acao=acao,
                custo=no.custo + custo_transicao,
                profundidade=no.profundidade + 1,
            )
        )
    return filhos


# ============================================================
# 1. BFS — Busca em largura (teste de objectivo na geração)
# ============================================================

def bfs(problema, estado_inicial=None, limite_expansoes=None, limite_segundos=None):
    def executar(resultado, inicio):
        inicial = _construir_no_inicial(problema, estado_inicial)
        resultado.nos_gerados = 1
        resultado.tamanho_maximo_fronteira = 1

        if problema.teste_objetivo(inicial.estado):
            _preencher_resultado_sucesso(resultado, inicial)
            return

        fronteira = deque([inicial])
        visitados = {_chave(problema, inicial.estado)}

        while fronteira:
            _verificar_limites(inicio, limite_segundos, resultado.nos_expandidos, limite_expansoes)
            atual = fronteira.popleft()
            resultado.nos_expandidos += 1

            for filho in _gerar_filhos(problema, atual, inicio, limite_segundos):
                chave = _chave(problema, filho.estado)
                if chave not in visitados:
                    resultado.nos_gerados += 1
                    if problema.teste_objetivo(filho.estado):
                        resultado.tamanho_maximo_fronteira = max(
                            resultado.tamanho_maximo_fronteira, len(fronteira)
                        )
                        _preencher_resultado_sucesso(resultado, filho)
                        return
                    visitados.add(chave)
                    fronteira.append(filho)

            resultado.tamanho_maximo_fronteira = max(
                resultado.tamanho_maximo_fronteira, len(fronteira)
            )

    return _executar_com_metricas("BFS", executar)


# ============================================================
# 2. DFS — Busca em profundidade (ciclos no caminho + limite)
# ============================================================

def dfs(
    problema,
    estado_inicial=None,
    limite_profundidade=None,
    limite_expansoes=None,
    limite_segundos=None,
):
    def executar(resultado, inicio):
        inicial = _construir_no_inicial(problema, estado_inicial)
        resultado.nos_gerados = 1
        resultado.tamanho_maximo_fronteira = 1

        if problema.teste_objetivo(inicial.estado):
            _preencher_resultado_sucesso(resultado, inicial)
            return

        chave_inicial = _chave(problema, inicial.estado)
        caminho_atual = {chave_inicial}
        # Pilha explícita: [no, chave, lista_filhos_ou_None, proximo_indice]
        pilha = [[inicial, chave_inicial, None, 0]]

        while pilha:
            _verificar_limites(inicio, limite_segundos, resultado.nos_expandidos, limite_expansoes)
            topo = pilha[-1]
            no_atual, chave_atual, filhos, idx = topo

            if filhos is None:
                if limite_profundidade is not None and no_atual.profundidade >= limite_profundidade:
                    pilha.pop()
                    caminho_atual.remove(chave_atual)
                    continue

                resultado.nos_expandidos += 1
                filhos = _gerar_filhos(problema, no_atual, inicio, limite_segundos)
                topo[2] = filhos

            if idx >= len(filhos):
                pilha.pop()
                caminho_atual.remove(chave_atual)
                continue

            filho = filhos[idx]
            topo[3] = idx + 1
            chave_filho = _chave(problema, filho.estado)

            if chave_filho in caminho_atual:
                continue

            resultado.nos_gerados += 1
            if problema.teste_objetivo(filho.estado):
                _preencher_resultado_sucesso(resultado, filho)
                return

            caminho_atual.add(chave_filho)
            pilha.append([filho, chave_filho, None, 0])
            resultado.tamanho_maximo_fronteira = max(
                resultado.tamanho_maximo_fronteira, len(pilha)
            )

    return _executar_com_metricas("DFS", executar)


# ============================================================
# 3. IDS — Aprofundamento iterativo (com re-expansões)
# ============================================================

def ids(
    problema,
    estado_inicial=None,
    limite_profundidade=100,
    limite_expansoes=None,
    limite_segundos=None,
):
    def executar(resultado, inicio):
        inicial = _construir_no_inicial(problema, estado_inicial)
        resultado.nos_gerados = 1
        resultado.tamanho_maximo_fronteira = 1

        expandidos_anteriores = set()

        def pesquisa_limitada(no, limite, caminho_atual):
            _verificar_limites(inicio, limite_segundos, resultado.nos_expandidos, limite_expansoes)

            if problema.teste_objetivo(no.estado):
                return no, False

            if no.profundidade >= limite:
                return None, True

            chave_no = _chave(problema, no.estado)
            if chave_no in expandidos_anteriores:
                resultado.nos_reexpandidos += 1
            else:
                expandidos_anteriores.add(chave_no)

            resultado.nos_expandidos += 1
            houve_corte = False

            filhos = _gerar_filhos(problema, no, inicio, limite_segundos)
            for filho in filhos:
                chave = _chave(problema, filho.estado)
                if chave in caminho_atual:
                    continue

                resultado.nos_gerados += 1
                caminho_atual.add(chave)
                resultado.tamanho_maximo_fronteira = max(
                    resultado.tamanho_maximo_fronteira, len(caminho_atual)
                )

                solucao, cortou = pesquisa_limitada(filho, limite, caminho_atual)
                if solucao is not None:
                    return solucao, False
                if cortou:
                    houve_corte = True

                caminho_atual.remove(chave)

            return None, houve_corte

        for limite in range(limite_profundidade + 1):
            caminho_atual = {_chave(problema, inicial.estado)}
            solucao, houve_corte = pesquisa_limitada(inicial, limite, caminho_atual)

            if solucao is not None:
                _preencher_resultado_sucesso(resultado, solucao)
                return

            if not houve_corte:
                resultado.motivo = "Não foi encontrada uma solução."
                return

        resultado.motivo = "Limite de profundidade atingido."

    return _executar_com_metricas("IDS", executar)


# ============================================================
# 4. UCS — Custo uniforme
# ============================================================

def ucs(problema, estado_inicial=None, limite_expansoes=None, limite_segundos=None):
    def executar(resultado, inicio):
        inicial = _construir_no_inicial(problema, estado_inicial)
        sequencia = count()
        fronteira = [(0.0, next(sequencia), inicial)]
        melhor_custo = {_chave(problema, inicial.estado): 0.0}

        resultado.nos_gerados = 1
        resultado.tamanho_maximo_fronteira = 1

        while fronteira:
            _verificar_limites(inicio, limite_segundos, resultado.nos_expandidos, limite_expansoes)
            custo_atual, _, atual = heapq.heappop(fronteira)
            chave_atual = _chave(problema, atual.estado)

            if custo_atual > melhor_custo.get(chave_atual, float("inf")):
                continue

            if problema.teste_objetivo(atual.estado):
                _preencher_resultado_sucesso(resultado, atual)
                return

            resultado.nos_expandidos += 1

            for filho in _gerar_filhos(problema, atual, inicio, limite_segundos):
                chave = _chave(problema, filho.estado)
                if filho.custo < melhor_custo.get(chave, float("inf")):
                    melhor_custo[chave] = filho.custo
                    heapq.heappush(fronteira, (filho.custo, next(sequencia), filho))
                    resultado.nos_gerados += 1

            resultado.tamanho_maximo_fronteira = max(
                resultado.tamanho_maximo_fronteira, len(fronteira)
            )

    return _executar_com_metricas("UCS", executar)


# ============================================================
# 5. Gulosa — Greedy Best-First Search
# ============================================================

def gulosa(problema, heuristica, estado_inicial=None, limite_expansoes=None, limite_segundos=None):
    def executar(resultado, inicio):
        inicial = _construir_no_inicial(problema, estado_inicial)
        sequencia = count()
        h_ini = heuristica(inicial.estado, problema)
        fronteira = [(h_ini, next(sequencia), inicial)]
        visitados = {_chave(problema, inicial.estado)}

        resultado.nos_gerados = 1
        resultado.tamanho_maximo_fronteira = 1

        while fronteira:
            _verificar_limites(inicio, limite_segundos, resultado.nos_expandidos, limite_expansoes)
            _, _, atual = heapq.heappop(fronteira)

            if problema.teste_objetivo(atual.estado):
                _preencher_resultado_sucesso(resultado, atual)
                return

            resultado.nos_expandidos += 1

            for filho in _gerar_filhos(problema, atual, inicio, limite_segundos):
                chave = _chave(problema, filho.estado)
                if chave not in visitados:
                    visitados.add(chave)
                    h_val = heuristica(filho.estado, problema)
                    if h_val == float("inf"):
                        continue
                    heapq.heappush(fronteira, (h_val, next(sequencia), filho))
                    resultado.nos_gerados += 1

            resultado.tamanho_maximo_fronteira = max(
                resultado.tamanho_maximo_fronteira, len(fronteira)
            )

    return _executar_com_metricas("Gulosa", executar)


# ============================================================
# 6. A* — A estrela
# ============================================================

def a_estrela(problema, heuristica, estado_inicial=None, limite_expansoes=None, limite_segundos=None):
    def executar(resultado, inicio):
        inicial = _construir_no_inicial(problema, estado_inicial)
        sequencia = count()
        h_ini = heuristica(inicial.estado, problema)
        fronteira = [(h_ini, next(sequencia), inicial)]
        melhor_custo = {_chave(problema, inicial.estado): 0.0}

        resultado.nos_gerados = 1
        resultado.tamanho_maximo_fronteira = 1

        while fronteira:
            _verificar_limites(inicio, limite_segundos, resultado.nos_expandidos, limite_expansoes)
            _, _, atual = heapq.heappop(fronteira)
            chave_atual = _chave(problema, atual.estado)

            if atual.custo > melhor_custo.get(chave_atual, float("inf")):
                continue

            if problema.teste_objetivo(atual.estado):
                _preencher_resultado_sucesso(resultado, atual)
                return

            resultado.nos_expandidos += 1

            for filho in _gerar_filhos(problema, atual, inicio, limite_segundos):
                chave = _chave(problema, filho.estado)
                if filho.custo < melhor_custo.get(chave, float("inf")):
                    h_val = heuristica(filho.estado, problema)
                    if h_val == float("inf"):
                        continue
                    melhor_custo[chave] = filho.custo
                    heapq.heappush(fronteira, (filho.custo + h_val, next(sequencia), filho))
                    resultado.nos_gerados += 1

            resultado.tamanho_maximo_fronteira = max(
                resultado.tamanho_maximo_fronteira, len(fronteira)
            )

    return _executar_com_metricas("A*", executar)


# ============================================================
# 7. DFBnB — Depth-First Branch and Bound
# ============================================================

def dfbnb(problema, heuristica, estado_inicial=None, limite_expansoes=None, limite_segundos=None):
    def executar(resultado, inicio):
        inicial = _construir_no_inicial(problema, estado_inicial)
        melhor_solucao = None
        limite = float("inf")

        resultado.nos_gerados = 1
        resultado.tamanho_maximo_fronteira = 1
        caminho_atual = {_chave(problema, inicial.estado)}

        def explorar(atual):
            nonlocal melhor_solucao, limite

            _verificar_limites(inicio, limite_segundos, resultado.nos_expandidos, limite_expansoes)

            if problema.teste_objetivo(atual.estado):
                if atual.custo < limite:
                    limite = atual.custo
                    melhor_solucao = atual
                return

            resultado.nos_expandidos += 1
            filhos = _gerar_filhos(problema, atual, inicio, limite_segundos)
            resultado.nos_gerados += len(filhos)

            filhos_avaliados = []
            for filho in filhos:
                f_val = filho.custo + heuristica(filho.estado, problema)
                if f_val < limite:
                    filhos_avaliados.append((f_val, filho))

            filhos_avaliados.sort(key=lambda item: item[0])

            for f_val, filho in filhos_avaliados:
                # O limite pode ter baixado após explorar irmãos anteriores.
                if f_val >= limite:
                    break

                chave = _chave(problema, filho.estado)
                if chave in caminho_atual:
                    continue

                caminho_atual.add(chave)
                resultado.tamanho_maximo_fronteira = max(
                    resultado.tamanho_maximo_fronteira, len(caminho_atual)
                )
                explorar(filho)
                caminho_atual.remove(chave)

        explorar(inicial)

        if melhor_solucao is not None:
            _preencher_resultado_sucesso(resultado, melhor_solucao)

    return _executar_com_metricas("DFBnB", executar)


# ============================================================
# Despachante e apresentação
# ============================================================

def executar_busca(
    problema,
    algoritmo,
    heuristica=None,
    estado_inicial=None,
    limite_expansoes=None,
    limite_segundos=None,
):
    nome = algoritmo.strip().upper()

    if nome == "BFS":
        return bfs(problema, estado_inicial, limite_expansoes, limite_segundos)
    if nome == "DFS":
        return dfs(
            problema,
            estado_inicial=estado_inicial,
            limite_expansoes=limite_expansoes,
            limite_segundos=limite_segundos,
        )
    if nome == "IDS":
        return ids(
            problema,
            estado_inicial=estado_inicial,
            limite_expansoes=limite_expansoes,
            limite_segundos=limite_segundos,
        )
    if nome == "UCS":
        return ucs(problema, estado_inicial, limite_expansoes, limite_segundos)

    if nome in ("GULOSA", "GREEDY"):
        if heuristica is None:
            raise ValueError("A busca Gulosa precisa de uma heurística.")
        return gulosa(problema, heuristica, estado_inicial, limite_expansoes, limite_segundos)

    if nome in ("A*", "ASTAR"):
        if heuristica is None:
            raise ValueError("A* precisa de uma heurística.")
        return a_estrela(problema, heuristica, estado_inicial, limite_expansoes, limite_segundos)

    if nome == "DFBNB":
        if heuristica is None:
            raise ValueError("DFBnB precisa de uma heurística.")
        return dfbnb(problema, heuristica, estado_inicial, limite_expansoes, limite_segundos)

    raise ValueError(f"Algoritmo desconhecido: {algoritmo}")


def apresentar_resultado(resultado):
    print("\n========== RESULTADO DA PESQUISA ==========")
    print(f"Algoritmo: {resultado.algoritmo}")
    print(f"Sucesso: {'Sim' if resultado.sucesso else 'Não'}")
    print(f"Mensagem: {resultado.motivo}")

    if resultado.sucesso:
        print(f"Custo da solução: {resultado.custo_solucao:.4f}")
        print(f"Comprimento do caminho: {resultado.comprimento_caminho}")

    print(f"Nós expandidos: {resultado.nos_expandidos}")
    print(f"Nós gerados: {resultado.nos_gerados}")
    if resultado.algoritmo == "IDS" or resultado.nos_reexpandidos > 0:
        print(f"Nós re-expandidos: {resultado.nos_reexpandidos}")
    print(f"Máximo da fronteira: {resultado.tamanho_maximo_fronteira}")
    print(f"Tempo: {resultado.tempo_segundos:.4f} segundos")
    print(f"Memória de pico: {resultado.memoria_pico_mb:.4f} MB")
    print("===========================================\n")