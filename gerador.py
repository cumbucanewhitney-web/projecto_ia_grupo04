"""
gerador.py
Geração automática de instâncias para o problema P4.

Grupo 04 - Laboral
Semente oficial: 202604
"""

import argparse
import json
import random
from pathlib import Path


SEMENTE_GRUPO = 202604

SALAS_PADRAO = [
    {"id": "S1", "capacidade": 40},
    {"id": "S2", "capacidade": 60},
    {"id": "S3", "capacidade": 80},
    {"id": "S4", "capacidade": 120},
]

NIVEIS = {
    "pequena": {
        "num_disciplinas": 5,
        "dias": 3,
        "periodos_por_dia": 2,
        "num_salas": 3,
        "num_docentes": 6,
        "grandes": 1,
        "probabilidade_conflito": 0.25,
        "partilhados_min": 1,
        "partilhados_max": 8,
    },
    "media": {
        "num_disciplinas": 9,
        "dias": 4,
        "periodos_por_dia": 2,
        "num_salas": 4,
        "num_docentes": 6,
        "grandes": 1,
        "probabilidade_conflito": 0.35,
        "partilhados_min": 3,
        "partilhados_max": 18,
    },
    "grande": {
        "num_disciplinas": 14,
        "dias": 5,
        "periodos_por_dia": 2,
        "num_salas": 4,
        "num_docentes": 8,
        "grandes": 2,
        "probabilidade_conflito": 0.50,
        "partilhados_min": 5,
        "partilhados_max": 35,
    },
}


def criar_slots_referencia(rng, num_disciplinas, num_slots, num_grandes):
    """
    Distribui as disciplinas por slots de referência de modo a garantir que
    existem soluções válidas (exames grandes ficam sozinhos num slot).
    """
    slots = list(range(num_grandes))
    restantes_slots = list(range(num_grandes, num_slots))
    faltam = num_disciplinas - num_grandes

    # Repetir slots apenas o necessário, nunca pondo mais de 2 exames por slot.
    extras_necessarios = max(0, faltam - len(restantes_slots))
    pool = restantes_slots + rng.sample(restantes_slots, extras_necessarios)
    rng.shuffle(pool)
    slots.extend(pool[:faltam])
    return slots


def _gerar_instancia_com_rng(rng, nivel, numero, semente):
    if nivel not in NIVEIS:
        raise ValueError(f"Nível inválido: {nivel}.")

    cfg = NIVEIS[nivel]
    num_disciplinas = cfg["num_disciplinas"]
    dias = cfg["dias"]
    periodos = cfg["periodos_por_dia"]
    num_slots = dias * periodos
    salas = SALAS_PADRAO[-cfg["num_salas"]:]
    docentes = [f"V{i}" for i in range(1, cfg["num_docentes"] + 1)]
    num_grandes = cfg["grandes"]

    slots_ref = criar_slots_referencia(rng, num_disciplinas, num_slots, num_grandes)

    # Contar quantas disciplinas partilham cada slot na referência para garantir
    # que duas disciplinas no mesmo slot cabem simultaneamente em 1 sala cada (<=120 e <=80).
    por_slot = {}
    for idx, sl in enumerate(slots_ref):
        por_slot.setdefault(sl, []).append(idx)

    inscritos_por_idx = [0] * num_disciplinas
    for sl, idxs in por_slot.items():
        if len(idxs) == 1 and idxs[0] < num_grandes:
            inscritos_por_idx[idxs[0]] = rng.randint(125, 175)
        elif len(idxs) == 1:
            inscritos_por_idx[idxs[0]] = rng.randint(25, 115)
        else:
            # 2 disciplinas no mesmo slot: uma até 115 (cabe em S4=120), outra até 80 (cabe em S3=80)
            inscritos_por_idx[idxs[0]] = rng.randint(25, 115)
            inscritos_por_idx[idxs[1]] = rng.randint(25, 78)

    disciplinas = [
        {
            "id": f"D{i + 1:02d}",
            "nome": f"Disciplina {i + 1:02d}",
            "inscritos": inscritos_por_idx[i],
        }
        for i in range(num_disciplinas)
    ]

    matriz = [[0 for _ in range(num_disciplinas)] for _ in range(num_disciplinas)]
    prob = cfg["probabilidade_conflito"]
    p_min = cfg["partilhados_min"]
    p_max = cfg["partilhados_max"]

    for i in range(num_disciplinas):
        for j in range(i + 1, num_disciplinas):
            if slots_ref[i] == slots_ref[j]:
                continue
            if rng.random() < prob:
                limite = min(disciplinas[i]["inscritos"], disciplinas[j]["inscritos"], p_max)
                if limite >= p_min:
                    partilhados = rng.randint(p_min, limite)
                    matriz[i][j] = partilhados
                    matriz[j][i] = partilhados

    return {
        "metadata": {
            "grupo": 4,
            "turno": "Laboral",
            "nivel": nivel,
            "numero": numero,
            "semente": semente,
        },
        "num_disciplinas": num_disciplinas,
        "dias": dias,
        "periodos_por_dia": periodos,
        "num_slots": num_slots,
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


def gerar_instancia(nivel="pequena", seed=SEMENTE_GRUPO, numero=1):
    if nivel not in NIVEIS:
        raise ValueError(f"Nível desconhecido: {nivel}")
    rng = random.Random(seed + numero - 1)
    return _gerar_instancia_com_rng(rng, nivel, numero, seed + numero - 1)


def guardar_instancia(instancia, caminho):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as ficheiro:
        json.dump(instancia, ficheiro, indent=4, ensure_ascii=False)


def carregar_instancia(caminho):
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"Ficheiro não encontrado: {caminho}")
    with open(caminho, "r", encoding="utf-8") as ficheiro:
        return json.load(ficheiro)


def gerar_conjunto_instancias(diretorio="instancias", seed=SEMENTE_GRUPO, quantidade_por_nivel=10):
    rng = random.Random(seed)
    diretorio = Path(diretorio)
    total = 0

    for nivel in ("pequena", "media", "grande"):
        pasta_nivel = diretorio / nivel
        pasta_nivel.mkdir(parents=True, exist_ok=True)
        for numero in range(1, quantidade_por_nivel + 1):
            instancia = _gerar_instancia_com_rng(rng, nivel, numero, seed)
            guardar_instancia(instancia, pasta_nivel / f"instancia_{numero:02d}.json")
            total += 1

    print(f"Geração concluída: {total} instâncias criadas em {diretorio.resolve()} (seed={seed}).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerador de instâncias do problema P4.")
    parser.add_argument("--seed", type=int, default=SEMENTE_GRUPO)
    parser.add_argument("--quantidade", type=int, default=10)
    parser.add_argument("--diretorio", type=str, default="instancias")
    args = parser.parse_args()

    gerar_conjunto_instancias(
        diretorio=args.diretorio,
        seed=args.seed,
        quantidade_por_nivel=args.quantidade,
    )