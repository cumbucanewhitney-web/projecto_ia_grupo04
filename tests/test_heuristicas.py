"""
tests/test_heuristicas.py
Testes de admissibilidade, consistência, dominância e b* em heuristicas.py.
"""

from collections import deque

import pytest

from buscas import a_estrela
from dominio import CalendarioExames
from heuristicas import (
    calcular_factor_ramificacao_efectivo,
    h0,
    h1,
    h2,
    testar_admissibilidade,
    testar_consistencia,
)


def _enumerar_estados_alcancaveis(problema):
    fila = deque([problema.estado_inicial()])
    visitados = {problema.estado_inicial()}
    while fila:
        atual = fila.popleft()
        for acao in problema.acoes(atual):
            seguinte = problema.resultado(atual, acao)
            if seguinte not in visitados:
                visitados.add(seguinte)
                fila.append(seguinte)
    return list(visitados)


def test_dominancia_h2_sobre_h1(problema_pequeno):
    s0 = problema_pequeno.estado_inicial()
    estados = [s0] + [problema_pequeno.resultado(s0, a) for a in problema_pequeno.acoes(s0)[:5]]

    for s in estados:
        assert h0(s, problema_pequeno) <= h1(s, problema_pequeno) + 1e-9
        assert h1(s, problema_pequeno) <= h2(s, problema_pequeno) + 1e-9


def test_admissibilidade_todos_estados_instancia_pequena(make_instancia):
    dados = make_instancia(
        num_disciplinas=3,
        dias=2,
        periodos_por_dia=2,
        inscritos=[35, 50, 28],
        matriz=[[0, 4, 0], [4, 0, 3], [0, 3, 0]],
    )
    problema = CalendarioExames(dados)
    estados = _enumerar_estados_alcancaveis(problema)

    assert len(estados) > 10

    rel_h1 = testar_admissibilidade(problema, estados, h1)
    rel_h2 = testar_admissibilidade(problema, estados, h2)

    assert rel_h1["admissivel"] is True
    assert rel_h1["falhas"] == 0
    assert rel_h2["admissivel"] is True
    assert rel_h2["falhas"] == 0


def test_consistencia_h1_todos_estados_instancia_pequena(make_instancia):
    dados = make_instancia(
        num_disciplinas=3,
        dias=2,
        periodos_por_dia=2,
        inscritos=[35, 50, 28],
        matriz=[[0, 4, 0], [4, 0, 3], [0, 3, 0]],
    )
    problema = CalendarioExames(dados)
    estados = _enumerar_estados_alcancaveis(problema)

    rel = testar_consistencia(problema, estados, h1)
    assert rel["consistente_nos_estados_testados"] is True
    assert rel["contraexemplos"] == []


def test_interface_problema_heuristica_e_b_estrela(problema_pequeno):
    s0 = problema_pequeno.estado_inicial()
    assert problema_pequeno.heuristica(s0, "h0") == pytest.approx(0.0)
    assert problema_pequeno.heuristica(s0, "h1") == pytest.approx(h1(s0, problema_pequeno))
    assert problema_pequeno.heuristica(s0, "h2") == pytest.approx(h2(s0, problema_pequeno))

    res = a_estrela(problema_pequeno, h2)
    b_estrela = calcular_factor_ramificacao_efectivo(
        res.nos_expandidos,
        res.comprimento_caminho,
    )
    assert b_estrela >= 0.0