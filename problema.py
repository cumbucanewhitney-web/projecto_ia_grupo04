"""
problema.py
Estrutura genérica para problemas de busca em Inteligência Artificial.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar


Estado = TypeVar("Estado")
Acao = TypeVar("Acao")


class Problema(ABC, Generic[Estado, Acao]):
    """Classe abstracta base para problemas de busca no espaço de estados."""

    def __init__(self, estado_inicial: Estado):
        self._estado_inicial = estado_inicial

    def estado_inicial(self) -> Estado:
        """Devolve o estado inicial do problema."""
        return self._estado_inicial

    @abstractmethod
    def acoes(self, estado: Estado) -> list[Acao]:
        """Devolve as acções possíveis a partir de um estado."""
        raise NotImplementedError

    def accoes(self, estado: Estado) -> list[Acao]:
        """Alias conforme nomenclatura do enunciado."""
        return self.acoes(estado)

    @abstractmethod
    def resultado(self, estado: Estado, acao: Acao) -> Estado:
        """Aplica uma acção a um estado e devolve o novo estado."""
        raise NotImplementedError

    @abstractmethod
    def custo(self, estado: Estado, acao: Acao, novo_estado: Estado) -> float:
        """Devolve o custo não negativo da transição."""
        raise NotImplementedError

    @abstractmethod
    def teste_objetivo(self, estado: Estado) -> bool:
        """Verifica se o estado é objectivo."""
        raise NotImplementedError

    def e_objectivo(self, estado: Estado) -> bool:
        """Alias conforme nomenclatura do enunciado."""
        return self.teste_objetivo(estado)

    def heuristica(self, estado: Estado, nome: str = "h1") -> float:
        """Calcula a heurística indicada pelo nome (por omissão h=0)."""
        return 0.0

    def sucessores(self, estado: Estado):
        """Produz pares (acção, novo_estado) a partir de um estado."""
        for acao in self.acoes(estado):
            yield acao, self.resultado(estado, acao)

    def chave_estado(self, estado: Estado) -> Any:
        """Devolve uma chave hashable para identificar o estado."""
        try:
            hash(estado)
            return estado
        except TypeError:
            return repr(estado)


@dataclass(eq=False)
class No(Generic[Estado, Acao]):
    """Representa um nó na árvore de busca."""

    estado: Estado
    pai: "No | None" = None
    acao: Acao | None = None
    custo: float = 0.0
    profundidade: int = 0

    @property
    def g(self) -> float:
        """Alias para o custo acumulado g(n)."""
        return self.custo

    def filho(self, problema: Problema, acao: Acao) -> "No":
        """Cria um nó filho aplicando uma acção."""
        novo_estado = problema.resultado(self.estado, acao)
        custo_passo = problema.custo(self.estado, acao, novo_estado)

        if custo_passo < 0:
            raise ValueError("O custo de uma acção não pode ser negativo.")

        return No(
            estado=novo_estado,
            pai=self,
            acao=acao,
            custo=self.custo + custo_passo,
            profundidade=self.profundidade + 1,
        )

    def caminho_nos(self) -> list["No"]:
        """Reconstrói a sequência de nós desde a raiz até este nó."""
        lista = []
        atual = self
        while atual is not None:
            lista.append(atual)
            atual = atual.pai
        lista.reverse()
        return lista

    def solucao(self) -> list[Acao]:
        """Devolve a sequência de acções desde a raiz até este nó."""
        return [no.acao for no in self.caminho_nos()[1:]]

    def estados_caminho(self) -> list[Estado]:
        """Devolve a sequência de estados desde a raiz até este nó."""
        return [no.estado for no in self.caminho_nos()]

    def __repr__(self) -> str:
        return f"No(g={self.custo:.2f}, profundidade={self.profundidade})"


def caminho(no: No) -> list[No]:
    """Função exigida pelo enunciado para reconstruir o caminho até ao nó."""
    return no.caminho_nos()