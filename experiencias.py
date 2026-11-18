"""
experiencias.py

Executa experiências sobre as instâncias do projecto.

Responsabilidades:
- Encontrar instâncias JSON (3 pequenas, 2 médias e 1 grande).
- Executar os sete algoritmos.
- Testar h1 e h2 nos algoritmos informados.
- Registar métricas.
- Exportar resultados para CSV.
- Gerar três gráficos.

Os limites definidos são:
- 60 segundos por execução.
- 2 GB de memória de pico.

NOTA:
Os limites são passados aos algoritmos e verificados durante a pesquisa.
As execuções que excedem qualquer limite ficam registadas como FALHOU no CSV.
"""

import csv
import time
from pathlib import Path
from statistics import mean

from gerador import carregar_instancia
from dominio import CalendarioExames
from buscas import executar_busca
from heuristicas import h1, h2


# ============================================================
# CONFIGURAÇÕES
# ============================================================

PASTA_INSTANCIAS = Path("instancias")
PASTA_RESULTADOS = Path("resultados")
PASTA_GRAFICOS = PASTA_RESULTADOS / "graficos"

FICHEIRO_CSV = PASTA_RESULTADOS / "resultados.csv"

LIMITE_TEMPO = 60
LIMITE_MEMORIA_MB = 2048

HEURISTICAS = {
    "h1": h1,
    "h2": h2
}

NUMERO_INSTANCIAS_POR_NIVEL = {
    "pequena": 3,
    "media": 2,
    "grande": 1
}


# ============================================================
# DESCOBRIR INSTÂNCIAS
# ============================================================

def encontrar_instancias():
    """
    Procura todos os ficheiros JSON dentro da pasta instancias/.

    Exemplo:
        instancias/pequena/instancia_01.json
        instancias/media/instancia_01.json
        instancias/grande/instancia_01.json
    """
    if not PASTA_INSTANCIAS.exists():
        return []

    return sorted(PASTA_INSTANCIAS.rglob("*.json"))


def identificar_nivel(caminho):
    """Obtém o nível a partir do nome da pasta da instância."""
    for parte in caminho.parts:
        if parte.lower() in ("pequena", "media", "grande"):
            return parte.lower()

    return "nao_identificado"


def selecionar_instancias(instancias):
    """Selecciona um número limitado e determinístico por nível."""
    instancias = list(instancias)
    selecionadas = []

    for nivel, quantidade in NUMERO_INSTANCIAS_POR_NIVEL.items():
        do_nivel = sorted(
            caminho
            for caminho in instancias
            if identificar_nivel(caminho) == nivel
        )
        selecionadas.extend(do_nivel[:quantidade])

    return selecionadas


# ============================================================
# CONFIGURAR EXPERIÊNCIAS
# ============================================================

def obter_algoritmos():
    """
    Define os algoritmos e as heurísticas a experimentar.

    UCS é executado primeiro para servir de referência do custo
    óptimo, quando consegue encontrar uma solução dentro do limite.
    """
    return [
        ("UCS", None),

        ("BFS", None),
        ("DFS", None),
        ("IDS", None),

        ("Gulosa", h1),
        ("Gulosa", h2),

        ("A*", h1),
        ("A*", h2),

        ("DFBnB", h1),
        ("DFBnB", h2)
    ]


# ============================================================
# EXECUTAR UMA EXPERIÊNCIA
# ============================================================

def executar_experiencia(
    problema,
    algoritmo,
    heuristica=None
):
    """
    Executa um algoritmo e recolhe as métricas.

    O tempo e a memória são medidos pelo próprio buscas.py,
    através de perf_counter() e tracemalloc. A pesquisa é interrompida
    quando ultrapassa qualquer um dos limites.
    """
    inicio = time.perf_counter()

    try:
        resultado = executar_busca(
            problema=problema,
            algoritmo=algoritmo,
            heuristica=heuristica,
            limite_segundos=LIMITE_TEMPO,
            limite_memoria_mb=LIMITE_MEMORIA_MB
        )

        tempo_total = time.perf_counter() - inicio
        memoria_mb = resultado.memoria_pico_mb

        # Verificar se o limite de memória foi ultrapassado.
        if memoria_mb > LIMITE_MEMORIA_MB:
            estado = "FALHOU"
            motivo = "Limite de memória ultrapassado."

        elif tempo_total > LIMITE_TEMPO:
            estado = "FALHOU"
            motivo = "Limite de tempo ultrapassado."

        elif not resultado.sucesso:
            estado = "FALHOU"
            motivo = resultado.motivo

        else:
            estado = "SUCESSO"
            motivo = ""

        return {
            "resultado": resultado,
            "estado": estado,
            "motivo": motivo,
            "tempo_total": tempo_total,
            "memoria_mb": memoria_mb
        }

    except MemoryError as erro:
        tempo_total = time.perf_counter() - inicio

        return {
            "resultado": None,
            "estado": "FALHOU",
            "motivo": str(erro) or "Limite de memória excedido.",
            "tempo_total": tempo_total,
            "memoria_mb": LIMITE_MEMORIA_MB
        }

    except Exception as erro:
        tempo_total = time.perf_counter() - inicio

        return {
            "resultado": None,
            "estado": "ERRO",
            "motivo": str(erro),
            "tempo_total": tempo_total,
            "memoria_mb": 0.0
        }


# ============================================================
# CONSTRUIR REGISTO PARA O CSV
# ============================================================

def construir_registo(
    caminho_instancia,
    nivel,
    tamanho,
    algoritmo,
    nome_heuristica,
    execucao,
    custo_otimo
):
    """Transforma uma execução numa linha do CSV."""

    resultado = execucao["resultado"]

    if resultado is None:
        custo = ""
        comprimento = ""
        expandidos = ""
        gerados = ""
        fronteira = ""
        tempo = execucao["tempo_total"]
        memoria = execucao["memoria_mb"]

    else:
        custo = (
            resultado.custo_solucao
            if resultado.sucesso
            else ""
        )

        comprimento = resultado.comprimento_caminho
        expandidos = resultado.nos_expandidos
        gerados = resultado.nos_gerados
        fronteira = resultado.tamanho_maximo_fronteira
        tempo = resultado.tempo_segundos
        memoria = resultado.memoria_pico_mb

    diferenca_custo = ""

    if custo != "" and custo_otimo is not None:
        diferenca_custo = float(custo) - custo_otimo

    return {
        "instancia": str(caminho_instancia),
        "nivel": nivel,
        "tamanho_instancia": tamanho,
        "algoritmo": algoritmo,
        "heuristica": nome_heuristica,
        "estado": execucao["estado"],
        "custo_solucao": custo,
        "custo_otimo": (
            custo_otimo if custo_otimo is not None else ""
        ),
        "diferenca_custo": diferenca_custo,
        "comprimento_caminho": comprimento,
        "nos_expandidos": expandidos,
        "nos_gerados": gerados,
        "fronteira_maxima": fronteira,
        "tempo_segundos": tempo,
        "memoria_pico_mb": memoria,
        "motivo_falha": execucao["motivo"]
    }


# ============================================================
# EXECUTAR TODAS AS EXPERIÊNCIAS
# ============================================================

def executar_todas_experiencias():
    """
    Executa todos os algoritmos sobre 3 instâncias pequenas,
    2 médias e 1 grande.

    Cada instância é carregada uma vez.
    O custo óptimo de referência é obtido através do UCS.
    Se o UCS falhar, o custo óptimo fica vazio no CSV.
    """
    PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    PASTA_GRAFICOS.mkdir(parents=True, exist_ok=True)

    instancias = selecionar_instancias(encontrar_instancias())

    if not instancias:
        print("Não foram encontradas instâncias.")
        print("Verifique a pasta instancias/.")
        return

    print(
        "Instâncias seleccionadas: "
        + ", ".join(
            f"{nivel}={sum(identificar_nivel(c) == nivel for c in instancias)}"
            for nivel in NUMERO_INSTANCIAS_POR_NIVEL
        )
    )

    registos = []

    for numero, caminho in enumerate(instancias, start=1):
        print("\n" + "=" * 60)
        print(f"INSTÂNCIA {numero}/{len(instancias)}")
        print(caminho)
        print("=" * 60)

        try:
            dados = carregar_instancia(caminho)
            problema = CalendarioExames(dados)

        except Exception as erro:
            print(f"Erro ao carregar a instância: {erro}")

            registos.append({
                "instancia": str(caminho),
                "nivel": identificar_nivel(caminho),
                "tamanho_instancia": "",
                "algoritmo": "",
                "heuristica": "",
                "estado": "ERRO",
                "custo_solucao": "",
                "custo_otimo": "",
                "diferenca_custo": "",
                "comprimento_caminho": "",
                "nos_expandidos": "",
                "nos_gerados": "",
                "fronteira_maxima": "",
                "tempo_segundos": 0,
                "memoria_pico_mb": 0,
                "motivo_falha": str(erro)
            })

            continue

        nivel = identificar_nivel(caminho)
        tamanho = len(problema.disciplinas)

        custo_otimo = None

        # UCS é a referência para determinar o custo óptimo.
        # Executa-se primeiro para evitar repetir a pesquisa.
        print("\nA executar UCS para obter o custo de referência...")

        execucao_ucs = executar_experiencia(
            problema,
            "UCS"
        )

        resultado_ucs = execucao_ucs["resultado"]

        if (
            execucao_ucs["estado"] == "SUCESSO"
            and resultado_ucs is not None
        ):
            custo_otimo = resultado_ucs.custo_solucao
            print(f"Custo de referência: {custo_otimo:.4f}")
        else:
            print("Não foi possível obter o custo óptimo com UCS.")

        registos.append(
            construir_registo(
                caminho,
                nivel,
                tamanho,
                "UCS",
                "",
                execucao_ucs,
                custo_otimo
            )
        )

        # Executar os restantes algoritmos.
        for algoritmo, heuristica in obter_algoritmos():
            if algoritmo == "UCS":
                continue

            nome_heuristica = (
                heuristica.__name__
                if heuristica is not None
                else ""
            )

            print(
                f"\nA executar {algoritmo}"
                + (
                    f" com {nome_heuristica}"
                    if nome_heuristica
                    else ""
                )
            )

            execucao = executar_experiencia(
                problema,
                algoritmo,
                heuristica
            )

            registo = construir_registo(
                caminho,
                nivel,
                tamanho,
                algoritmo,
                nome_heuristica,
                execucao,
                custo_otimo
            )

            registos.append(registo)

            print(f"Estado: {execucao['estado']}")
            print(f"Tempo: {execucao['tempo_total']:.3f} segundos")

            if execucao["resultado"] is not None:
                print(
                    "Nós expandidos: "
                    f"{execucao['resultado'].nos_expandidos}"
                )

            if execucao["motivo"]:
                print(f"Observação: {execucao['motivo']}")

        # Guardar o CSV após cada instância para não perder
        # os resultados das instâncias anteriores.
        exportar_csv(registos)

    exportar_csv(registos)
    criar_graficos()

    print("\nExperiências concluídas.")
    print(f"CSV: {FICHEIRO_CSV}")
    print(f"Gráficos: {PASTA_GRAFICOS}")


# ============================================================
# EXPORTAR CSV
# ============================================================

def exportar_csv(registos):
    """Exporta todos os registos para um ficheiro CSV."""

    PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)

    if not registos:
        return

    colunas = [
        "instancia",
        "nivel",
        "tamanho_instancia",
        "algoritmo",
        "heuristica",
        "estado",
        "custo_solucao",
        "custo_otimo",
        "diferenca_custo",
        "comprimento_caminho",
        "nos_expandidos",
        "nos_gerados",
        "fronteira_maxima",
        "tempo_segundos",
        "memoria_pico_mb",
        "motivo_falha"
    ]

    with open(
        FICHEIRO_CSV,
        "w",
        newline="",
        encoding="utf-8"
    ) as ficheiro:

        escritor = csv.DictWriter(
            ficheiro,
            fieldnames=colunas
        )

        escritor.writeheader()
        escritor.writerows(registos)

    print(f"\nCSV actualizado: {FICHEIRO_CSV}")


# ============================================================
# CARREGAR RESULTADOS DO CSV
# ============================================================

def carregar_resultados_csv():
    """Lê os resultados já guardados no CSV."""

    if not FICHEIRO_CSV.exists():
        print("O ficheiro CSV ainda não existe.")
        return []

    with open(
        FICHEIRO_CSV,
        "r",
        newline="",
        encoding="utf-8"
    ) as ficheiro:

        return list(csv.DictReader(ficheiro))


# ============================================================
# GRÁFICO 1 — NÓS EXPANDIDOS VS TAMANHO
# ============================================================

def grafico_nos_expandidos(registos):
    """
    Compara a média de nós expandidos por tamanho da instância.

    O eixo vertical utiliza escala logarítmica.
    """
    import matplotlib.pyplot as plt

    dados = {}

    for registo in registos:
        if registo["estado"] != "SUCESSO":
            continue

        try:
            tamanho = int(registo["tamanho_instancia"])
            nos = int(registo["nos_expandidos"])
        except (ValueError, TypeError):
            continue

        nome = registo["algoritmo"]
        if registo["heuristica"]:
            nome += "-" + registo["heuristica"]

        dados.setdefault(nome, {}).setdefault(tamanho, []).append(max(1, nos))

    plt.figure(figsize=(10, 6))

    for nome, por_tamanho in dados.items():
        tamanhos = sorted(por_tamanho)
        medias = [mean(por_tamanho[t]) for t in tamanhos]
        plt.plot(tamanhos, medias, marker="o", label=nome)

    plt.yscale("log")
    plt.xlabel("Tamanho da instância (número de disciplinas)")
    plt.ylabel("Nós expandidos - média (escala logarítmica)")
    plt.title("Nós expandidos vs. tamanho da instância")
    plt.legend()
    plt.grid(True, which="both", linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig(
        PASTA_GRAFICOS / "nos_expandidos_vs_tamanho.png"
    )
    plt.close()


# ============================================================
# GRÁFICO 2 — TEMPO VS TAMANHO
# ============================================================

def grafico_tempo(registos):
    """Compara a média do tempo de execução por tamanho da instância."""
    import matplotlib.pyplot as plt

    dados = {}

    for registo in registos:
        if registo["estado"] == "ERRO":
            continue

        try:
            tamanho = int(registo["tamanho_instancia"])
            tempo = float(registo["tempo_segundos"])
        except (ValueError, TypeError):
            continue

        nome = registo["algoritmo"]
        if registo["heuristica"]:
            nome += "-" + registo["heuristica"]

        dados.setdefault(nome, {}).setdefault(tamanho, []).append(tempo)

    plt.figure(figsize=(10, 6))

    for nome, por_tamanho in dados.items():
        tamanhos = sorted(por_tamanho)
        medias = [mean(por_tamanho[t]) for t in tamanhos]
        plt.plot(tamanhos, medias, marker="o", label=nome)

    plt.xlabel("Tamanho da instância (número de disciplinas)")
    plt.ylabel("Tempo médio de execução (segundos)")
    plt.title("Tempo de execução vs. tamanho da instância")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig(
        PASTA_GRAFICOS / "tempo_vs_tamanho.png"
    )
    plt.close()


# ============================================================
# GRÁFICO 3 — CUSTO OBTIDO VS CUSTO ÓPTIMO
# ============================================================

def grafico_custo_otimo(registos):
    """
    Compara o custo encontrado por cada algoritmo com o custo
    óptimo obtido pelo UCS.

    A linha diagonal representa custo obtido = custo óptimo.
    """
    import matplotlib.pyplot as plt

    dados = {}

    for registo in registos:
        if registo["estado"] != "SUCESSO":
            continue

        try:
            custo = float(registo["custo_solucao"])
            otimo = float(registo["custo_otimo"])
        except (ValueError, TypeError):
            continue

        nome = registo["algoritmo"]
        if registo["heuristica"]:
            nome += "-" + registo["heuristica"]

        dados.setdefault(nome, []).append((otimo, custo))

    plt.figure(figsize=(8, 8))

    marcadores = ["o", "s", "^", "D", "v", "P", "X", "*", "<", ">"]
    todos_os_valores = []

    for idx, (nome, valores) in enumerate(dados.items()):
        x = [item[0] for item in valores]
        y = [item[1] for item in valores]

        todos_os_valores.extend(x)
        todos_os_valores.extend(y)

        plt.scatter(
            x,
            y,
            marker=marcadores[idx % len(marcadores)],
            s=max(35, 110 - idx * 8),
            alpha=0.75,
            label=nome
        )

    if todos_os_valores:
        minimo = min(todos_os_valores)
        maximo = max(todos_os_valores)

        plt.plot(
            [minimo, maximo],
            [minimo, maximo],
            linestyle="--",
            color="black",
            label="Custo óptimo"
        )

    plt.xlabel("Custo óptimo (UCS)")
    plt.ylabel("Custo obtido")
    plt.title("Custo obtido vs. custo óptimo")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig(
        PASTA_GRAFICOS / "custo_vs_otimo.png"
    )
    plt.close()


# ============================================================
# CRIAR TODOS OS GRÁFICOS
# ============================================================

def criar_graficos():
    """Cria os três gráficos obrigatórios a partir do CSV."""

    registos = carregar_resultados_csv()

    if not registos:
        print("Não existem resultados para criar gráficos.")
        return

    PASTA_GRAFICOS.mkdir(parents=True, exist_ok=True)

    try:
        grafico_nos_expandidos(registos)
        grafico_tempo(registos)
        grafico_custo_otimo(registos)

    except ImportError:
        print(
            "Não foi possível criar os gráficos. "
            "Instale matplotlib com: pip install matplotlib"
        )
        return

    print("\nGráficos criados:")
    print("- nos_expandidos_vs_tamanho.png")
    print("- tempo_vs_tamanho.png")
    print("- custo_vs_otimo.png")


# ============================================================
# EXECUÇÃO DIRECTA
# ============================================================

if __name__ == "__main__":
    executar_todas_experiencias()