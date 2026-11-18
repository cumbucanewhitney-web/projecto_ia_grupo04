"""
tests/test_dominio.py
Testes do domínio P4 (CalendarioExames) e do gerador de instâncias.
"""

import pytest

from dominio import Acao, CalendarioExames
from gerador import SEMENTE_GRUPO, gerar_instancia


def test_estado_inicial_imutavel_e_hashable(problema_pequeno):
    s0 = problema_pequeno.estado_inicial()

    assert s0.disciplinas_marcadas == 0
    assert s0.completo is False
    assert len(s0.atribuicoes) == 4
    assert all(a is None for a in s0.atribuicoes)

    explorados = {s0}
    assert s0 in explorados


def test_sucessores_estado_conhecido(make_instancia):
    dados = make_instancia(
        num_disciplinas=2,
        dias=1,
        periodos_por_dia=2,
        inscritos=[35, 50],
        matriz=[[0, 3], [3, 0]],
        salas=[
            {"id": "S1", "capacidade": 40},
            {"id": "S2", "capacidade": 60},
        ],
        docentes=["V1", "V2", "V3", "V4"],
    )
    problema = CalendarioExames(dados)
    s0 = problema.estado_inicial()

    # D02 (50 inscritos) tem mais inscritos -> vai primeiro e só cabe em S2 nos 2 slots.
    assert problema.proxima_disciplina(s0) == 1
    sucessores = list(problema.sucessores(s0))
    assert len(sucessores) == 2

    for acao, novo_estado in sucessores:
        assert acao.disciplina_id == "D02"
        assert acao.salas == ("S2",)
        assert len(acao.vigilantes) == 2
        assert novo_estado.disciplinas_marcadas == 1


def test_transicao_nao_altera_estado_anterior(problema_pequeno):
    s0 = problema_pequeno.estado_inicial()
    acao = problema_pequeno.acoes(s0)[0]
    s1 = problema_pequeno.resultado(s0, acao)

    assert s0.disciplinas_marcadas == 0
    assert s1.disciplinas_marcadas == 1
    assert s0 != s1


def test_conflito_estudantes_mesmo_slot_proibido(make_instancia):
    dados = make_instancia(
        num_disciplinas=2,
        dias=1,
        periodos_por_dia=2,
        inscritos=[30, 30],
        matriz=[[0, 4], [4, 0]],
    )
    problema = CalendarioExames(dados)
    s0 = problema.estado_inicial()

    acao_slot_0 = [a for a in problema.acoes(s0) if a.slot == 0][0]
    s1 = problema.resultado(s0, acao_slot_0)

    acoes_s1 = problema.acoes(s1)
    assert len(acoes_s1) > 0
    assert all(a.slot != 0 for a in acoes_s1)

    idx_segunda = problema.proxima_disciplina(s1)
    acao_ilegal = Acao(
        disciplina_indice=idx_segunda,
        disciplina_id=problema.disciplinas[idx_segunda].id,
        slot=0,
        salas=("S2",),
        vigilantes_por_sala=(("V3", "V4"),),
    )
    with pytest.raises(ValueError):
        problema.resultado(s1, acao_ilegal, validar=True)


def test_calculo_custos_mesmo_dia_consecutivo_e_lugares_vazios(make_instancia):
    dados = make_instancia(
        num_disciplinas=2,
        dias=3,
        periodos_por_dia=2,
        inscritos=[35, 30],
        matriz=[[0, 5], [5, 0]],
    )
    problema = CalendarioExames(dados)
    s0 = problema.estado_inicial()

    acao_d1 = [a for a in problema.acoes(s0) if a.slot == 0 and a.salas == ("S1",)][0]
    s1 = problema.resultado(s0, acao_d1)
    assert problema.custo(s0, acao_d1, s1) == pytest.approx(5 * 0.01)

    # Mesmo dia (slot 1, dia 0): 5 * 3 + 10 * 0.01 = 15.10
    acao_mesmo_dia = [a for a in problema.acoes(s1) if a.slot == 1 and a.salas == ("S1",)][0]
    assert problema.custo(s1, acao_mesmo_dia, problema.resultado(s1, acao_mesmo_dia)) == pytest.approx(15.10)

    # Dia consecutivo (slot 2, dia 1): 5 * 1 + 10 * 0.01 = 5.10
    acao_consec = [a for a in problema.acoes(s1) if a.slot == 2 and a.salas == ("S1",)][0]
    assert problema.custo(s1, acao_consec, problema.resultado(s1, acao_consec)) == pytest.approx(5.10)

    # Dois dias depois (slot 4, dia 2): 0 + 10 * 0.01 = 0.10
    acao_afastado = [a for a in problema.acoes(s1) if a.slot == 4 and a.salas == ("S1",)][0]
    assert problema.custo(s1, acao_afastado, problema.resultado(s1, acao_afastado)) == pytest.approx(0.10)


def test_exame_grande_usa_duas_salas_e_quatro_vigilantes(make_instancia):
    dados = make_instancia(
        num_disciplinas=2,
        dias=2,
        periodos_por_dia=1,
        inscritos=[90, 30],
    )
    problema = CalendarioExames(dados)
    acoes = problema.acoes(problema.estado_inicial())

    assert len(acoes) > 0
    for acao in acoes:
        assert len(acao.salas) == 2
        assert len(acao.vigilantes) == 4
        assert len(set(acao.vigilantes)) == 4


def test_gerador_reprodutivel_e_tabela_valida():
    inst_1 = gerar_instancia(nivel="pequena", seed=SEMENTE_GRUPO, numero=1)
    inst_2 = gerar_instancia(nivel="pequena", seed=SEMENTE_GRUPO, numero=1)
    inst_3 = gerar_instancia(nivel="pequena", seed=SEMENTE_GRUPO, numero=2)

    assert inst_1 == inst_2
    assert inst_1 != inst_3

    problema = CalendarioExames(inst_1)
    assert problema.num_disciplinas == 5