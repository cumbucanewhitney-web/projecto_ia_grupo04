"""
tests/conftest.py
Configuração global e fixtures partilhadas pelo pytest.
"""

from pathlib import Path
import sys

import pytest

RAIZ_PROJECTO = Path(__file__).resolve().parent.parent
if str(RAIZ_PROJECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJECTO))

from dominio import CalendarioExames


@pytest.fixture
def make_instancia():
    """Fábrica de instâncias pequenas e determinísticas para testes."""
    def _criar(
        num_disciplinas=3,
        dias=2,
        periodos_por_dia=2,
        inscritos=None,
        matriz=None,
        salas=None,
        docentes=None,
    ):
        if inscritos is None:
            inscritos = [30] * num_disciplinas
        if matriz is None:
            matriz = [[0] * num_disciplinas for _ in range(num_disciplinas)]
        if salas is None:
            salas = [
                {"id": "S1", "capacidade": 40},
                {"id": "S2", "capacidade": 60},
            ]
        if docentes is None:
            docentes = ["V1", "V2", "V3", "V4"]

        disciplinas = [
            {"id": f"D{i + 1:02d}", "nome": f"Disciplina {i + 1:02d}", "inscritos": inscritos[i]}
            for i in range(num_disciplinas)
        ]

        return {
            "num_disciplinas": num_disciplinas,
            "dias": dias,
            "periodos_por_dia": periodos_por_dia,
            "num_slots": dias * periodos_por_dia,
            "disciplinas": disciplinas,
            "matriz_estudantes_partilhados": matriz,
            "salas": salas,
            "docentes": docentes,
            "regras": {
                "vigilantes_por_sala": 2,
                "max_vigilancias_por_docente": 4,
                "penalizacao_mesmo_dia": 3,
                "penalizacao_dias_consecutivos": 1,
                "penalizacao_lugar_vazio": 0.01,
            },
        }

    return _criar


@pytest.fixture
def problema_pequeno(make_instancia):
    """Instância padrão de 4 disciplinas com conflitos e penalizações."""
    matriz = [
        [0, 5, 2, 0],
        [5, 0, 0, 4],
        [2, 0, 0, 3],
        [0, 4, 3, 0],
    ]
    dados = make_instancia(
        num_disciplinas=4,
        dias=3,
        periodos_por_dia=2,
        inscritos=[55, 35, 70, 40],
        matriz=matriz,
        salas=[
            {"id": "S1", "capacidade": 40},
            {"id": "S2", "capacidade": 60},
            {"id": "S3", "capacidade": 80},
        ],
        docentes=["V1", "V2", "V3", "V4", "V5", "V6"],
    )
    return CalendarioExames(dados)