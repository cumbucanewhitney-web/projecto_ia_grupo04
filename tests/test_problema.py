"""
tests/test_problema.py
Testes unitários à estrutura genérica em problema.py.
"""

import pytest

from problema import No, Problema, caminho


class ProblemaLinearDummy(Problema[int, int]):
    """Problema simples de inteiros para validar a interface genérica."""

    def __init__(self, inicio=0, objetivo=3, custo_negativo=False):
        super().__init__(inicio)
        self.objetivo = objetivo
        self.custo_negativo = custo_negativo

    def acoes(self, estado):
        return [1]

    def resultado(self, estado, acao):
        return estado + acao

    def custo(self, estado, acao, novo_estado):
        return -1.0 if self.custo_negativo else 2.5

    def teste_objetivo(self, estado):
        return estado == self.objetivo


def test_classe_abstrata_nao_pode_ser_instanciada():
    with pytest.raises(TypeError):
        Problema(0)


def test_no_filho_rejeita_custo_negativo():
    prob = ProblemaLinearDummy(custo_negativo=True)
    raiz = No(estado=prob.estado_inicial())

    with pytest.raises(ValueError):
        raiz.filho(prob, 1)


def test_reconstrucao_caminho_e_funcao_caminho():
    prob = ProblemaLinearDummy(inicio=0, objetivo=2)
    n0 = No(estado=prob.estado_inicial())
    n1 = n0.filho(prob, 1)
    n2 = n1.filho(prob, 1)

    assert n2.g == pytest.approx(5.0)
    assert n2.profundidade == 2
    assert n2.solucao() == [1, 1]
    assert n2.estados_caminho() == [0, 1, 2]
    assert caminho(n2) == [n0, n1, n2]