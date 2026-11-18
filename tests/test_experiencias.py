import pytest

import experiencias


def test_selecionar_instancias_limita_por_nivel(tmp_path):
    instancias = []
    for nivel in ("pequena", "media", "grande"):
        for numero in range(1, 11):
            caminho = tmp_path / nivel / f"instancia_{numero:02d}.json"
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.touch()
            instancias.append(caminho)

    selecionadas = experiencias.selecionar_instancias(reversed(instancias))

    assert len(selecionadas) == 6
    assert [
        experiencias.identificar_nivel(caminho)
        for caminho in selecionadas
    ] == ["pequena", "pequena", "pequena", "media", "media", "grande"]
    assert [caminho.name for caminho in selecionadas] == [
        "instancia_01.json",
        "instancia_02.json",
        "instancia_03.json",
        "instancia_01.json",
        "instancia_02.json",
        "instancia_01.json",
    ]


def test_criar_graficos_exporta_os_tres_png(tmp_path, monkeypatch):
    pasta_resultados = tmp_path / "resultados"
    pasta_graficos = pasta_resultados / "graficos"
    ficheiro_csv = pasta_resultados / "resultados.csv"
    monkeypatch.setattr(experiencias, "PASTA_RESULTADOS", pasta_resultados)
    monkeypatch.setattr(experiencias, "PASTA_GRAFICOS", pasta_graficos)
    monkeypatch.setattr(experiencias, "FICHEIRO_CSV", ficheiro_csv)
    experiencias.exportar_csv([{
        "instancia": "instancia_01.json",
        "nivel": "pequena",
        "tamanho_instancia": 4,
        "algoritmo": "BFS",
        "heuristica": "",
        "estado": "SUCESSO",
        "custo_solucao": 10,
        "custo_otimo": 9,
        "diferenca_custo": 1,
        "comprimento_caminho": 4,
        "nos_expandidos": 3,
        "nos_gerados": 5,
        "fronteira_maxima": 2,
        "tempo_segundos": 0.1,
        "memoria_pico_mb": 1,
        "motivo_falha": "",
    }])

    experiencias.criar_graficos()

    assert {
        caminho.name for caminho in pasta_graficos.glob("*.png")
    } == {
        "nos_expandidos_vs_tamanho.png",
        "tempo_vs_tamanho.png",
        "custo_vs_otimo.png",
    }


@pytest.mark.parametrize(
    ("nome_limite", "valor_limite", "motivo_esperado"),
    [
        ("LIMITE_TEMPO", 1e-12, "Limite de tempo"),
        ("LIMITE_MEMORIA_MB", 1e-9, "Limite de memória"),
    ],
)
def test_limite_excedido_falha_e_fica_no_csv(
    problema_pequeno,
    tmp_path,
    monkeypatch,
    nome_limite,
    valor_limite,
    motivo_esperado
):
    pasta_resultados = tmp_path / "resultados"
    ficheiro_csv = pasta_resultados / "resultados.csv"
    monkeypatch.setattr(experiencias, nome_limite, valor_limite)
    monkeypatch.setattr(experiencias, "PASTA_RESULTADOS", pasta_resultados)
    monkeypatch.setattr(experiencias, "FICHEIRO_CSV", ficheiro_csv)

    execucao = experiencias.executar_experiencia(problema_pequeno, "BFS")

    assert execucao["estado"] == "FALHOU"
    assert motivo_esperado in execucao["motivo"]

    registo = experiencias.construir_registo(
        "instancias/pequena/instancia_01.json",
        "pequena",
        len(problema_pequeno.disciplinas),
        "BFS",
        "",
        execucao,
        None
    )
    experiencias.exportar_csv([registo])

    resultados = experiencias.carregar_resultados_csv()
    assert len(resultados) == 1
    assert resultados[0]["estado"] == "FALHOU"
    assert motivo_esperado in resultados[0]["motivo_falha"]
