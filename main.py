
"""
main.py

Ponto de entrada do projecto.

Permite:
- Carregar instâncias existentes.
- Gerar novas instâncias.
- Seleccionar algoritmos e heurísticas.
- Definir limites.
- Executar pesquisas.
- Visualizar a solução passo a passo.
- Consultar métricas.
"""

import json
from pathlib import Path

from gerador import (
    carregar_instancia,
    gerar_instancia
)

from dominio import CalendarioExames

from heuristicas import h1, h2

from buscas import (
    executar_busca,
    apresentar_resultado
)


# ============================================================
# CONFIGURAÇÕES
# ============================================================

PASTA_INSTANCIAS = Path("instancias")

SEED_GRUPO = 202604

HEURISTICAS = {
    "1": ("h1", h1),
    "2": ("h2", h2)
}

ALGORITMOS = {
    "1": "BFS",
    "2": "DFS",
    "3": "IDS",
    "4": "UCS",
    "5": "Gulosa",
    "6": "A*",
    "7": "DFBnB"
}


# ============================================================
# APRESENTAÇÃO
# ============================================================

def apresentar_titulo():
    """Apresenta o cabeçalho do programa."""

    print("\n" + "=" * 60)
    print("        PROJECTO DE INTELIGÊNCIA ARTIFICIAL")
    print("             CALENDÁRIO DE EXAMES")
    print("                  GRUPO 04")
    print("=" * 60)


def apresentar_menu_principal():
    """Apresenta as opções principais."""

    print("\nMENU PRINCIPAL")
    print("-" * 40)
    print("1. Carregar uma instância existente")
    print("2. Gerar uma nova instância")
    print("3. Executar experiências")
    print("0. Sair")
    print("-" * 40)


# ============================================================
# INPUTS
# ============================================================

def ler_inteiro(mensagem, minimo=None, maximo=None):
    """Lê um número inteiro e valida os limites."""

    while True:
        try:
            valor = int(input(mensagem))

            if minimo is not None and valor < minimo:
                print(f"Introduza um valor igual ou superior a {minimo}.")
                continue

            if maximo is not None and valor > maximo:
                print(f"Introduza um valor igual ou inferior a {maximo}.")
                continue

            return valor

        except ValueError:
            print("Valor inválido. Introduza um número inteiro.")


def ler_limite_tempo():
    """Lê o limite de tempo em segundos."""

    while True:
        try:
            valor = float(
                input("Limite de tempo em segundos (ex.: 60): ")
            )

            if valor <= 0:
                print("O limite deve ser superior a zero.")
                continue

            return valor

        except ValueError:
            print("Introduza um número válido.")


# ============================================================
# CARREGAR INSTÂNCIA
# ============================================================

def listar_instancias():
    """Procura os ficheiros JSON disponíveis."""

    if not PASTA_INSTANCIAS.exists():
        return []

    return sorted(PASTA_INSTANCIAS.rglob("*.json"))


def seleccionar_instancia():
    """Permite escolher uma instância existente."""

    instancias = listar_instancias()

    if not instancias:
        print("\nNão existem instâncias disponíveis.")
        return None

    print("\nINSTÂNCIAS DISPONÍVEIS")
    print("-" * 40)

    for indice, caminho in enumerate(instancias, start=1):
        print(f"{indice}. {caminho}")

    print("0. Voltar")

    escolha = ler_inteiro(
        "\nSeleccione uma instância: ",
        minimo=0,
        maximo=len(instancias)
    )

    if escolha == 0:
        return None

    caminho = instancias[escolha - 1]

    try:
        dados = carregar_instancia(caminho)
        problema = CalendarioExames(dados)

        print("\nInstância carregada com sucesso.")
        print(f"Ficheiro: {caminho}")
        print(
            f"Número de disciplinas: "
            f"{len(problema.disciplinas)}"
        )
        print(
            f"Número de salas: "
            f"{len(problema.salas)}"
        )

        return problema

    except Exception as erro:
        print(f"\nErro ao carregar a instância: {erro}")
        return None


# ============================================================
# GERAR NOVA INSTÂNCIA
# ============================================================

def gerar_nova_instancia():
    """
    Gera uma nova instância e guarda-a em formato JSON.

    A função gerar_instancia pertence a gerador.py.
    Este ficheiro trata apenas da interacção com o utilizador
    e da gravação dos dados.
    """

    print("\nGERAR NOVA INSTÂNCIA")
    print("-" * 40)
    print("1. Pequena")
    print("2. Média")
    print("3. Grande")

    escolha = ler_inteiro(
        "Seleccione o nível: ",
        minimo=1,
        maximo=3
    )

    niveis = {
        1: "pequena",
        2: "media",
        3: "grande"
    }

    nivel = niveis[escolha]

    numero = ler_inteiro(
        "Número da instância (ex.: 1): ",
        minimo=1
    )

    seed = SEED_GRUPO + numero - 1

    try:
        print("\nA gerar instância...")

        # A geração dos dados é responsabilidade de gerador.py.
        dados = gerar_instancia(
            nivel=nivel,
            seed=seed
        )

        pasta_destino = PASTA_INSTANCIAS / nivel
        pasta_destino.mkdir(parents=True, exist_ok=True)

        caminho = pasta_destino / f"instancia_{numero:02d}.json"

        # Guardar os dados em JSON.
        with open(
            caminho,
            "w",
            encoding="utf-8"
        ) as ficheiro:

            json.dump(
                dados,
                ficheiro,
                ensure_ascii=False,
                indent=4
            )

        print("\nInstância gerada e guardada com sucesso.")
        print(f"Ficheiro: {caminho}")
        print(f"Seed utilizada: {seed}")

        return CalendarioExames(dados)

    except Exception as erro:
        print(f"\nErro ao gerar a instância: {erro}")
        return None


# ============================================================
# SELECCIONAR ALGORITMO
# ============================================================

def seleccionar_algoritmo():
    """Permite seleccionar um dos sete algoritmos."""

    print("\nSELECCIONAR ALGORITMO")
    print("-" * 40)

    for numero, nome in ALGORITMOS.items():
        print(f"{numero}. {nome}")

    escolha = input("\nOpção: ").strip()

    if escolha not in ALGORITMOS:
        print("Opção inválida.")
        return None

    return ALGORITMOS[escolha]


# ============================================================
# SELECCIONAR HEURÍSTICA
# ============================================================

def seleccionar_heuristica():
    """Permite escolher h1 ou h2."""

    print("\nSELECCIONAR HEURÍSTICA")
    print("-" * 40)
    print("1. h1 - Desperdício mínimo global")
    print("2. h2 - Desperdício considerando salas livres")

    escolha = input("\nOpção: ").strip()

    if escolha not in HEURISTICAS:
        print("Opção inválida.")
        return None

    return HEURISTICAS[escolha]


# ============================================================
# VISUALIZAR SOLUÇÃO
# ============================================================

def nome_dia(slot):
    """Converte um slot no dia correspondente."""

    dias = [
        "Segunda-feira",
        "Terça-feira",
        "Quarta-feira",
        "Quinta-feira",
        "Sexta-feira"
    ]

    indice = slot // 2

    if 0 <= indice < len(dias):
        return dias[indice]

    return f"Dia {indice + 1}"


def nome_periodo(slot):
    """Converte um slot no período correspondente."""

    if slot % 2 == 0:
        return "Manhã"

    return "Tarde"


def visualizar_solucao(resultado):
    """Apresenta as acções da solução passo a passo."""

    if not resultado.sucesso:
        print("\nNão existe uma solução para visualizar.")
        return

    if not resultado.acoes_solucao:
        print("\nO estado inicial já é uma solução.")
        return

    print("\n" + "=" * 60)
    print("             CALENDÁRIO DE EXAMES")
    print("=" * 60)

    total = len(resultado.acoes_solucao)

    for indice, acao in enumerate(
        resultado.acoes_solucao,
        start=1
    ):
        slot = acao.slot

        print(f"\nPASSO {indice}/{total}")
        print("-" * 40)

        print(f"Disciplina: {acao.disciplina_id}")
        print(f"Slot: {slot}")
        print(f"Dia: {nome_dia(slot)}")
        print(f"Período: {nome_periodo(slot)}")

        print("\nSalas atribuídas:")

        for sala_id in acao.salas:
            print(f"  - Sala {sala_id}")

        print("\nVigilantes:")

        for sala_id, pares in zip(
            acao.salas,
            acao.vigilantes_por_sala
        ):
            print(f"  Sala {sala_id}: {pares[0]} e {pares[1]}")

        if indice < total:
            continuar = input(
                "\nPrima ENTER para ver o próximo passo..."
            )

    print("\n" + "=" * 60)
    print("             FIM DO CALENDÁRIO")
    print("=" * 60)


# ============================================================
# EXECUTAR PESQUISA
# ============================================================

def executar_pesquisa(problema):
    """Configura e executa uma pesquisa."""

    algoritmo = seleccionar_algoritmo()

    if algoritmo is None:
        return

    heuristica = None

    if algoritmo in ("Gulosa", "A*", "DFBnB"):
        seleccao = seleccionar_heuristica()

        if seleccao is None:
            return

        nome_heuristica, heuristica = seleccao

        print(f"\nHeurística seleccionada: {nome_heuristica}")

    print("\nLIMITES DE EXECUÇÃO")
    print("-" * 40)

    limite_tempo = ler_limite_tempo()

    limite_expansoes = input(
        "Limite de nós expandidos (ENTER para sem limite): "
    ).strip()

    if limite_expansoes == "":
        limite_expansoes = None
    else:
        try:
            limite_expansoes = int(limite_expansoes)

            if limite_expansoes <= 0:
                print("O limite deve ser superior a zero.")
                return

        except ValueError:
            print("Limite inválido.")
            return

    print("\nA iniciar a pesquisa...")
    print(f"Algoritmo: {algoritmo}")

    try:
        resultado = executar_busca(
            problema=problema,
            algoritmo=algoritmo,
            heuristica=heuristica,
            limite_expansoes=limite_expansoes,
            limite_segundos=limite_tempo
        )

        apresentar_resultado(resultado)

        if resultado.sucesso:
            opcao = input(
                "Deseja visualizar a solução passo a passo? (s/n): "
            ).strip().lower()

            if opcao == "s":
                visualizar_solucao(resultado)

    except Exception as erro:
        print(f"\nErro durante a pesquisa: {erro}")


# ============================================================
# MENU DE INSTÂNCIA
# ============================================================

def menu_instancia(problema):
    """Menu de operações sobre uma instância carregada."""

    while True:
        print("\nINSTÂNCIA CARREGADA")
        print("-" * 40)
        print("1. Executar pesquisa")
        print("2. Voltar ao menu principal")

        escolha = input("\nOpção: ").strip()

        if escolha == "1":
            executar_pesquisa(problema)

        elif escolha == "2":
            break

        else:
            print("Opção inválida.")


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():
    """Inicia o programa."""

    apresentar_titulo()

    while True:
        apresentar_menu_principal()

        escolha = input("\nSeleccione uma opção: ").strip()

        if escolha == "1":
            problema = seleccionar_instancia()

            if problema is not None:
                menu_instancia(problema)

        elif escolha == "2":
            problema = gerar_nova_instancia()

            if problema is not None:
                menu_instancia(problema)

        elif escolha == "3":
            from experiencias import executar_todas_experiencias

            executar_todas_experiencias()

        elif escolha == "0":
            print("\nPrograma terminado.")
            break

        else:
            print("\nOpção inválida. Tente novamente.")


if __name__ == "__main__":
    main()
