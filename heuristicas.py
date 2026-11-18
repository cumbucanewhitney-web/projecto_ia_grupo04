"""
heuristicas.py
Heurísticas para o problema do calendário de exames.

- h0: heurística nula (h = 0) para comparação no A*.
- h1: limite inferior admissível e consistente:
      desperdício mínimo global de lugares + menor penalização inevitável
      de cada disciplina não marcada contra as já marcadas.
- h2: limite inferior admissível dominante (h1 <= h2 <= h*):
      considera as salas livres e os docentes disponíveis em cada slot,
      além das penalizações inevitáveis entre pares de disciplinas ainda
      não marcadas cujos dias válidos obrigam distância <= 1.
"""

from itertools import combinations


def _disciplinas_restantes(estado, problema):
    """Devolve os índices das disciplinas ainda não atribuídas."""
    return [
        i for i in problema.ordem_disciplinas
        if estado.atribuicoes[i] is None
    ]


def _desperdicio_minimo(disciplina, salas_disponiveis):
    """Menor desperdício possível (1 ou 2 salas) ou None se não couber."""
    inscritos = disciplina.inscritos
    melhor = None

    for sala in salas_disponiveis:
        if sala.capacidade >= inscritos:
            desp = sala.capacidade - inscritos
            if melhor is None or desp < melhor:
                melhor = desp

    if len(salas_disponiveis) >= 2:
        for s1, s2 in combinations(salas_disponiveis, 2):
            cap = s1.capacidade + s2.capacidade
            if cap >= inscritos:
                desp = cap - inscritos
                if melhor is None or desp < melhor:
                    melhor = desp

    return melhor


def _penalidade_contra_marcadas(estado, problema, indice_disciplina, slot):
    """
    Calcula a penalização que `indice_disciplina` pagaria contra as disciplinas
    já marcadas caso fosse colocada em `slot`.
    Devolve None se houver conflito rígido no mesmo slot.
    """
    dia_atual = slot // problema.periodos_por_dia
    linha = problema.matriz_partilhados[indice_disciplina]
    penalidade = 0.0

    for idx, atrib in enumerate(estado.atribuicoes):
        if atrib is None:
            continue
        partilhados = linha[idx]
        if partilhados == 0:
            continue
        if atrib.slot == slot:
            return None

        diff = abs(dia_atual - (atrib.slot // problema.periodos_por_dia))
        if diff == 0:
            penalidade += partilhados * problema.penalizacao_mesmo_dia
        elif diff == 1:
            penalidade += partilhados * problema.penalizacao_dias_consecutivos

    return penalidade


def h0(estado, problema):
    """Heurística nula (0.0)."""
    return 0.0


def h1(estado, problema):
    """
    Heurística 1 (admissível e consistente):
    Para cada disciplina não marcada:
      min_desperdicio_global(d) * pen_vazio + min_{slot sem conflito}(pen_contra_marcadas(d, slot))
    """
    restantes = _disciplinas_restantes(estado, problema)
    if not restantes:
        return 0.0

    salas = problema.salas
    slots = problema.num_slots
    total = 0.0

    for indice in restantes:
        disciplina = problema.disciplinas[indice]
        desperdicio = _desperdicio_minimo(disciplina, salas)
        if desperdicio is None:
            return float("inf")

        melhor_pen = None
        for slot in range(slots):
            pen = _penalidade_contra_marcadas(estado, problema, indice, slot)
            if pen is None:
                continue
            if melhor_pen is None or pen < melhor_pen:
                melhor_pen = pen
                if melhor_pen == 0.0:
                    break

        if melhor_pen is None:
            return float("inf")

        total += desperdicio * problema.penalizacao_lugar_vazio + melhor_pen

    return total


def h2(estado, problema):
    """
    Heurística 2 (admissível e mais informada que h1):
    1. Para cada disciplina não marcada, calcula o menor custo imediato
       considerando salas livres e docentes disponíveis em cada slot.
    2. Verifica viabilidade global de vigilâncias.
    3. Soma o limite inferior inevitável entre pares ainda não marcados
       cujos dias viáveis obrigam a ficar no mesmo dia ou em dias consecutivos.
    """
    restantes = _disciplinas_restantes(estado, problema)
    if not restantes:
        return 0.0

    salas = problema.salas
    slots = problema.num_slots

    salas_ocupadas = [set() for _ in range(slots)]
    docentes_ocupados = [set() for _ in range(slots)]
    contagens = {d: 0 for d in problema.docentes}

    for atrib in estado.atribuicoes:
        if atrib is not None:
            salas_ocupadas[atrib.slot].update(atrib.salas)
            docentes_ocupados[atrib.slot].update(atrib.vigilantes)
            for d in atrib.vigilantes:
                contagens[d] += 1

    vigilancias_restantes = sum(problema.max_vigilancias_docente - contagens[d] for d in problema.docentes)
    min_vigilancias_necessarias = sum(
        problema._min_salas_disciplina[i] * problema.vigilantes_por_sala
        for i in restantes
    )
    if vigilancias_restantes < min_vigilancias_necessarias:
        return float("inf")

    total = 0.0
    dias_validos = {}

    for indice in restantes:
        disciplina = problema.disciplinas[indice]
        melhor_custo_i = None
        dias_i = set()

        for slot in range(slots):
            pen_marcadas = _penalidade_contra_marcadas(estado, problema, indice, slot)
            if pen_marcadas is None:
                continue

            docentes_livres = sum(
                1 for d in problema.docentes
                if d not in docentes_ocupados[slot] and contagens[d] < problema.max_vigilancias_docente
            )
            if docentes_livres < problema.vigilantes_por_sala:
                continue

            salas_livres = [s for s in salas if s.id not in salas_ocupadas[slot]]
            desperdicio_slot = None

            for s in salas_livres:
                if s.capacidade >= disciplina.inscritos:
                    desp = s.capacidade - disciplina.inscritos
                    if desperdicio_slot is None or desp < desperdicio_slot:
                        desperdicio_slot = desp

            if docentes_livres >= 2 * problema.vigilantes_por_sala and len(salas_livres) >= 2:
                for s1, s2 in combinations(salas_livres, 2):
                    cap = s1.capacidade + s2.capacidade
                    if cap >= disciplina.inscritos:
                        desp = cap - disciplina.inscritos
                        if desperdicio_slot is None or desp < desperdicio_slot:
                            desperdicio_slot = desp

            if desperdicio_slot is None:
                continue

            dias_i.add(slot // problema.periodos_por_dia)
            custo_slot = pen_marcadas + desperdicio_slot * problema.penalizacao_lugar_vazio
            if melhor_custo_i is None or custo_slot < melhor_custo_i:
                melhor_custo_i = custo_slot

        if melhor_custo_i is None:
            return float("inf")

        dias_validos[indice] = dias_i
        total += melhor_custo_i

    # Limite inferior entre pares ainda não marcados.
    for pos_a in range(len(restantes)):
        i = restantes[pos_a]
        dias_i = dias_validos[i]
        for pos_b in range(pos_a + 1, len(restantes)):
            j = restantes[pos_b]
            partilhados = problema.matriz_partilhados[i][j]
            if partilhados == 0:
                continue

            dias_j = dias_validos[j]
            # Menor penalização inevitável entre quaisquer d_i in dias_i e d_j in dias_j
            menor_pen_par = None
            for di in dias_i:
                for dj in dias_j:
                    diff = abs(di - dj)
                    if diff == 0:
                        p = partilhados * problema.penalizacao_mesmo_dia
                    elif diff == 1:
                        p = partilhados * problema.penalizacao_dias_consecutivos
                    else:
                        p = 0.0
                    if menor_pen_par is None or p < menor_pen_par:
                        menor_pen_par = p
                        if menor_pen_par == 0.0:
                            break
                if menor_pen_par == 0.0:
                    break

            if menor_pen_par is not None and menor_pen_par > 0.0:
                total += menor_pen_par

    return total


def testar_admissibilidade(problema, estados, heuristica, tolerancia=1e-9):
    """Testa h(s) <= h*(s) usando UCS em instâncias pequenas."""
    from buscas import ucs

    resultados = []
    falhas = []

    for numero, estado in enumerate(estados, start=1):
        resultado = ucs(problema, estado_inicial=estado)
        if not resultado.sucesso:
            continue

        estimativa = heuristica(estado, problema)
        custo_otimo = resultado.custo_solucao
        admissivel = estimativa <= custo_otimo + tolerancia

        registo = {
            "estado": numero,
            "heuristica": estimativa,
            "custo_otimo": custo_otimo,
            "admissivel": admissivel,
        }
        resultados.append(registo)
        if not admissivel:
            falhas.append(registo)

    return {
        "heuristica": heuristica.__name__,
        "estados_testados": len(resultados),
        "falhas": len(falhas),
        "admissivel": len(falhas) == 0,
        "detalhes": resultados,
        "falhas_detalhadas": falhas,
    }


def testar_consistencia(problema, estados, heuristica, tolerancia=1e-9):
    """Verifica h(s) <= c(s, a, s') + h(s') num conjunto de estados."""
    contraexemplos = []

    for estado in estados:
        valor_atual = heuristica(estado, problema)
        for acao in problema.acoes(estado):
            novo_estado = problema.resultado(estado, acao)
            custo_transicao = problema.custo(estado, acao, novo_estado)
            valor_seguinte = heuristica(novo_estado, problema)

            if valor_atual > custo_transicao + valor_seguinte + tolerancia:
                contraexemplos.append({
                    "estado": estado,
                    "acao": acao,
                    "h_atual": valor_atual,
                    "custo_transicao": custo_transicao,
                    "h_seguinte": valor_seguinte,
                })

    return {
        "heuristica": heuristica.__name__,
        "consistente_nos_estados_testados": len(contraexemplos) == 0,
        "contraexemplos": contraexemplos,
    }


def calcular_factor_ramificacao_efectivo(nos_expandidos, profundidade_solucao):
    """Calcula numericamente b* tal que N + 1 = 1 + b* + ... + (b*)^d."""
    if profundidade_solucao <= 0 or nos_expandidos <= 0:
        return 0.0

    objetivo = nos_expandidos + 1
    inferior = 0.0
    superior = max(2.0, float(nos_expandidos))

    for _ in range(100):
        meio = (inferior + superior) / 2
        soma = 1.0
        potencia = 1.0
        for _ in range(profundidade_solucao):
            potencia *= meio
            soma += potencia
        if soma < objetivo:
            inferior = meio
        else:
            superior = meio

    return (inferior + superior) / 2