"""
tests/test_buscas.py
Testes dos 7 algoritmos de pesquisa em buscas.py.
"""

import pytest

from buscas import a_estrela, bfs, dfbnb, dfs, executar_busca, gulosa, ids, ucs
from dominio import CalendarioExames
from heuristicas import h0, h1, h2


def test_instancia_sem_solucao_todos_algoritmos(make_instancia):
    # Triângulo de conflitos com apenas 2 slots -> sem solução possível.
    dados = make_instancia(
        num_disciplinas=3,
        dias=1,
        periodos_por_dia=2,
        inscritos=[30, 30, 30],
        matriz=[[0, 2, 2], [2, 0, 2], [2, 2, 0]],
    )
    problema = CalendarioExames(dados)

    for algoritmo, heur in [
        ("BFS", None),
        ("DFS", None),
        ("IDS", None),
        ("UCS", None),
        ("Gulosa", h1),
        ("Gulosa", h2),
        ("A*", h0),
        ("A*", h1),
        ("A*", h2),
        ("DFBnB", h1),
        ("DFBnB", h2),
    ]:
        res = executar_busca(problema, algoritmo, heuristica=heur)
        assert res.sucesso is False
        assert res.estado_solucao is None


def test_bfs_encontra_solucao_e_testa_objetivo_na_geracao(problema_pequeno):
    res = bfs(problema_pequeno)

    assert res.sucesso is True
    assert res.comprimento_caminho == 4
    assert problema_pequeno.e_objectivo(res.estado_solucao) is True

    # Se o estado inicial já for objectivo, devolve imediatamente sem expandir nós.
    res_direto = bfs(problema_pequeno, estado_inicial=res.estado_solucao)
    assert res_direto.sucesso is True
    assert res_direto.nos_expandidos == 0


def test_dfs_limite_profundidade_configuravel(problema_pequeno):
    res_curto = dfs(problema_pequeno, limite_profundidade=2)
    assert res_curto.sucesso is False

    res_ok = dfs(problema_pequeno, limite_profundidade=4)
    assert res_ok.sucesso is True
    assert problema_pequeno.teste_objetivo(res_ok.estado_solucao) is True


def test_ids_encontra_solucao_e_reporta_reexpansoes(problema_pequeno):
    res = ids(problema_pequeno, limite_profundidade=10)

    assert res.sucesso is True
    assert res.comprimento_caminho == 4
    assert res.nos_reexpandidos > 0
    assert problema_pequeno.teste_objetivo(res.estado_solucao) is True


def test_a_estrela_e_ucs_devolvem_mesmo_custo_otimo(problema_pequeno):
    res_ucs = ucs(problema_pequeno)
    res_a_h0 = a_estrela(problema_pequeno, h0)
    res_a_h1 = a_estrela(problema_pequeno, h1)
    res_a_h2 = a_estrela(problema_pequeno, h2)

    assert res_ucs.sucesso is True
    assert res_a_h0.custo_solucao == pytest.approx(res_ucs.custo_solucao)
    assert res_a_h1.custo_solucao == pytest.approx(res_ucs.custo_solucao)
    assert res_a_h2.custo_solucao == pytest.approx(res_ucs.custo_solucao)
    assert res_ucs.custo_solucao == pytest.approx(
        problema_pequeno.calcular_custo_total(res_ucs.estado_solucao)
    )


def test_dfbnb_e_ucs_devolvem_mesmo_custo_otimo(problema_pequeno):
    res_ucs = ucs(problema_pequeno)
    res_df_h1 = dfbnb(problema_pequeno, h1)
    res_df_h2 = dfbnb(problema_pequeno, h2)

    assert res_df_h1.sucesso is True
    assert res_df_h2.sucesso is True
    assert res_df_h1.custo_solucao == pytest.approx(res_ucs.custo_solucao)
    assert res_df_h2.custo_solucao == pytest.approx(res_ucs.custo_solucao)


def test_gulosa_encontra_solucao_e_gera_tabela_valida(problema_pequeno):
    for heur in (h1, h2):
        res = gulosa(problema_pequeno, heur)
        assert res.sucesso is True
        assert problema_pequeno.teste_objetivo(res.estado_solucao) is True

        tabela = problema_pequeno.solucao_para_tabela(res.estado_solucao)
        assert len(tabela) >= 4
        for linha in tabela:
            assert {"disciplina_id", "dia", "periodo", "slot", "sala", "vigilantes"} <= linha.keys()