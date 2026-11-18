import json
from types import SimpleNamespace

import main
from gerador import gerar_instancia


def test_seleccionar_instancia_por_dimensao_e_numero(
    tmp_path,
    monkeypatch,
    capsys
):
    pasta = tmp_path / "instancias" / "pequena"
    pasta.mkdir(parents=True)

    for numero in (3, 10):
        caminho = pasta / f"instancia_{numero:02d}.json"
        dados = gerar_instancia("pequena", numero=numero)
        caminho.write_text(json.dumps(dados), encoding="utf-8")

    monkeypatch.setattr(main, "PASTA_INSTANCIAS", tmp_path / "instancias")
    respostas = iter(("1", "2", "10"))
    monkeypatch.setattr("builtins.input", lambda _: next(respostas))

    problema = main.seleccionar_instancia()

    saida = capsys.readouterr().out
    assert len(problema.disciplinas) == 5
    assert "03, 10" in saida
    assert "Não existe uma instância com esse número." in saida
    assert "Ficheiro: " + str(pasta / "instancia_10.json") in saida
    assert "instancia_03.json" not in saida


def test_executar_pesquisa_usa_limite_fixo_de_60_segundos(
    monkeypatch,
    capsys
):
    argumentos = {}
    prompts = []

    monkeypatch.setattr(main, "seleccionar_algoritmo", lambda: "BFS")
    monkeypatch.setattr(
        main,
        "executar_busca",
        lambda **kwargs: (
            argumentos.update(kwargs) or SimpleNamespace(sucesso=False)
        )
    )
    monkeypatch.setattr(main, "apresentar_resultado", lambda _: None)
    monkeypatch.setattr(
        "builtins.input",
        lambda mensagem: prompts.append(mensagem) or ""
    )

    main.executar_pesquisa(object())

    saida = capsys.readouterr().out
    assert argumentos["limite_segundos"] == 60
    assert len(prompts) == 1
    assert "nós expandidos" in prompts[0]
    assert "Limite de tempo: 60 segundos." in saida
