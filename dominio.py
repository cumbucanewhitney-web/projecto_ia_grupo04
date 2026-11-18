"""
dominio.py
Representação do problema P4 - Calendário de Exames.

Grupo 04 - Laboral
"""

import json
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from problema import Problema


@dataclass(frozen=True)
class Disciplina:
    """Representa uma disciplina e o número de inscritos."""
    id: str
    nome: str
    inscritos: int


@dataclass(frozen=True)
class Sala:
    """Representa uma sala de exames."""
    id: str
    capacidade: int


@dataclass(frozen=True)
class Acao:
    """Representa a atribuição de uma disciplina ao calendário."""
    disciplina_indice: int
    disciplina_id: str
    slot: int
    salas: tuple[str, ...]
    vigilantes_por_sala: tuple[tuple[str, str], ...]

    @property
    def vigilantes(self):
        return tuple(
            docente
            for par in self.vigilantes_por_sala
            for docente in par
        )


@dataclass(frozen=True)
class Estado:
    """Representa um calendário parcial imutável e hashable."""
    atribuicoes: tuple[Acao | None, ...]

    def __hash__(self):
        return hash(self.atribuicoes)

    def __eq__(self, outro):
        if not isinstance(outro, Estado):
            return False
        return self.atribuicoes == outro.atribuicoes

    @property
    def disciplinas_marcadas(self):
        return sum(a is not None for a in self.atribuicoes)

    @property
    def completo(self):
        return all(a is not None for a in self.atribuicoes)


class CalendarioExames(Problema[Estado, Acao]):
    """Implementação concreta do problema P4."""

    def __init__(self, dados_instancia):
        if isinstance(dados_instancia, (str, Path)):
            with open(Path(dados_instancia), "r", encoding="utf-8") as f:
                dados_instancia = json.load(f)

        if not isinstance(dados_instancia, dict):
            raise TypeError("A instância deve ser um dicionário ou caminho JSON.")

        self.dados = dados_instancia
        self.num_disciplinas = int(dados_instancia["num_disciplinas"])
        self.dias = int(dados_instancia["dias"])
        self.periodos_por_dia = int(dados_instancia["periodos_por_dia"])
        self.num_slots = int(dados_instancia["num_slots"])

        self.disciplinas = tuple(
            Disciplina(
                id=item["id"],
                nome=item["nome"],
                inscritos=int(item["inscritos"]),
            )
            for item in dados_instancia["disciplinas"]
        )

        # Ordenar salas por capacidade crescente ajuda na organização.
        self.salas = tuple(
            sorted(
                (
                    Sala(id=item["id"], capacidade=int(item["capacidade"]))
                    for item in dados_instancia["salas"]
                ),
                key=lambda s: (s.capacidade, s.id),
            )
        )
        self.salas_por_id = {sala.id: sala for sala in self.salas}
        self.docentes = tuple(dados_instancia["docentes"])

        self.matriz_partilhados = tuple(
            tuple(int(valor) for valor in linha)
            for linha in dados_instancia["matriz_estudantes_partilhados"]
        )

        regras = dados_instancia.get("regras", {})
        self.vigilantes_por_sala = int(regras.get("vigilantes_por_sala", 2))
        self.max_vigilancias_docente = int(regras.get("max_vigilancias_por_docente", 4))
        self.penalizacao_mesmo_dia = float(regras.get("penalizacao_mesmo_dia", 3))
        self.penalizacao_dias_consecutivos = float(regras.get("penalizacao_dias_consecutivos", 1))
        self.penalizacao_lugar_vazio = float(regras.get("penalizacao_lugar_vazio", 0.01))

        self._validar_dados()

        # Estruturas auxiliares pré-calculadas para acelerar buscas e heurísticas.
        self._max_capacidade_1_sala = max(s.capacidade for s in self.salas)
        self._min_salas_disciplina = tuple(
            1 if d.inscritos <= self._max_capacidade_1_sala else 2
            for d in self.disciplinas
        )
        self._conflitos_mask = tuple(
            sum(
                (1 << j)
                for j in range(self.num_disciplinas)
                if self.matriz_partilhados[i][j] > 0
            )
            for i in range(self.num_disciplinas)
        )

        self.ordem_disciplinas = self._calcular_ordem_disciplinas()

        estado_inicial = Estado(
            atribuicoes=tuple(None for _ in range(self.num_disciplinas))
        )
        super().__init__(estado_inicial)

    def _validar_dados(self):
        if self.num_disciplinas != len(self.disciplinas):
            raise ValueError("O número de disciplinas não corresponde aos dados.")
        if self.num_slots != self.dias * self.periodos_por_dia:
            raise ValueError("num_slots deve ser igual a dias * periodos_por_dia.")
        if self.num_slots <= 0 or not self.disciplinas or not self.salas or not self.docentes:
            raise ValueError("Dados base da instância inválidos.")
        if self.vigilantes_por_sala != 2:
            raise ValueError("Este problema exige exatamente dois vigilantes por sala.")
        if self.max_vigilancias_docente <= 0:
            raise ValueError("O limite de vigilâncias deve ser positivo.")

        if len({d.id for d in self.disciplinas}) != len(self.disciplinas):
            raise ValueError("Existem IDs de disciplinas repetidos.")
        if len({s.id for s in self.salas}) != len(self.salas):
            raise ValueError("Existem IDs de salas repetidos.")
        if len(set(self.docentes)) != len(self.docentes):
            raise ValueError("Existem IDs de docentes repetidos.")

        if len(self.matriz_partilhados) != self.num_disciplinas:
            raise ValueError("Matriz de estudantes partilhados com dimensões inválidas.")

        for i, linha in enumerate(self.matriz_partilhados):
            if len(linha) != self.num_disciplinas or linha[i] != 0:
                raise ValueError("Matriz de estudantes partilhados inválida.")
            for j, valor in enumerate(linha):
                if valor < 0 or valor != self.matriz_partilhados[j][i]:
                    raise ValueError("A matriz deve ser não negativa e simétrica.")
                limite = min(self.disciplinas[i].inscritos, self.disciplinas[j].inscritos)
                if valor > limite:
                    raise ValueError(
                        f"Partilhados inválidos entre {self.disciplinas[i].id} e {self.disciplinas[j].id}."
                    )

        capacidade_duas_salas = sum(
            sorted((s.capacidade for s in self.salas), reverse=True)[:2]
        )
        for disciplina in self.disciplinas:
            if disciplina.inscritos <= 0:
                raise ValueError(f"A disciplina {disciplina.id} deve ter inscritos positivos.")
            if disciplina.inscritos > capacidade_duas_salas:
                raise ValueError(
                    f"A disciplina {disciplina.id} não cabe em nenhuma combinação de até 2 salas."
                )

    def _calcular_ordem_disciplinas(self):
        """
        Ordena as disciplinas mais restritas primeiro (MRV/Grau):
        1. Exames que exigem obrigatoriamente 2 salas primeiro.
        2. Maior grau de conflito.
        3. Maior total de estudantes partilhados.
        4. Maior número de inscritos.
        """
        itens = []
        for i, disciplina in enumerate(self.disciplinas):
            grau = sum(1 for j in range(self.num_disciplinas) if self.matriz_partilhados[i][j] > 0)
            total_partilhados = sum(self.matriz_partilhados[i])
            itens.append((
                -self._min_salas_disciplina[i],
                -grau,
                -total_partilhados,
                -disciplina.inscritos,
                disciplina.id,
                i,
            ))
        itens.sort()
        return tuple(item[-1] for item in itens)

    def proxima_disciplina(self, estado):
        """Devolve o índice da próxima disciplina a agendar."""
        for indice in self.ordem_disciplinas:
            if estado.atribuicoes[indice] is None:
                return indice
        return None

    def _salas_ocupadas(self, estado, slot):
        ocupadas = set()
        for atribuicao in estado.atribuicoes:
            if atribuicao is not None and atribuicao.slot == slot:
                ocupadas.update(atribuicao.salas)
        return ocupadas

    def _docentes_ocupados_no_slot(self, estado, slot):
        ocupados = set()
        for atribuicao in estado.atribuicoes:
            if atribuicao is not None and atribuicao.slot == slot:
                ocupados.update(atribuicao.vigilantes)
        return ocupados

    def _contar_vigilancias(self, estado):
        contagens = {docente: 0 for docente in self.docentes}
        for atribuicao in estado.atribuicoes:
            if atribuicao is not None:
                for docente in atribuicao.vigilantes:
                    contagens[docente] += 1
        return contagens

    def _tem_conflito_no_slot(self, estado, indice_disciplina, slot):
        mask_i = self._conflitos_mask[indice_disciplina]
        for indice, atribuicao in enumerate(estado.atribuicoes):
            if atribuicao is not None and atribuicao.slot == slot:
                if (mask_i >> indice) & 1:
                    return True
        return False

    def _atribuicao_canonica_vigilantes(self, docentes_disponiveis, contagens, numero_salas):
        """
        Quebra de simetria exacta:
        Como todos os docentes têm o mesmo custo (0) e as mesmas regras,
        escolher os docentes disponíveis com MENOR número de vigilâncias
        acumuladas maximiza a capacidade futura e preserva a existência de solução,
        reduzindo o factor de ramificação em 28x a 420x.
        """
        necessarios = numero_salas * self.vigilantes_por_sala
        if len(docentes_disponiveis) < necessarios:
            return None

        ordenados = sorted(docentes_disponiveis, key=lambda d: (contagens[d], d))
        escolhidos = ordenados[:necessarios]
        if numero_salas == 1:
            return ((escolhidos[0], escolhidos[1]),)
        return ((escolhidos[0], escolhidos[1]), (escolhidos[2], escolhidos[3]))

    def _custo_incremental_rapido(self, estado, indice_disciplina, slot, capacidade_total):
        """Calcula o custo incremental de colocar uma disciplina num slot/salas."""
        dia_atual = slot // self.periodos_por_dia
        custo_total = (capacidade_total - self.disciplinas[indice_disciplina].inscritos) * self.penalizacao_lugar_vazio

        linha = self.matriz_partilhados[indice_disciplina]
        for idx, atrib in enumerate(estado.atribuicoes):
            if atrib is None:
                continue
            partilhados = linha[idx]
            if partilhados == 0:
                continue
            diff = abs(dia_atual - (atrib.slot // self.periodos_por_dia))
            if diff == 0:
                custo_total += partilhados * self.penalizacao_mesmo_dia
            elif diff == 1:
                custo_total += partilhados * self.penalizacao_dias_consecutivos

        return custo_total

    def acoes(self, estado):
        """
        Gera as acções válidas para a próxima disciplina, aplicando:
        - Quebra de simetria nos vigilantes.
        - Forward checking de vigilâncias e de slots disponíveis para disciplinas futuras.
        - Poda de 2 salas quando existe 1 sala com menor desperdício no mesmo slot.
        - Ordenação por custo incremental (favorece DFS/DFBnB).
        """
        indice = self.proxima_disciplina(estado)
        if indice is None:
            return []

        disciplina = self.disciplinas[indice]
        contagens = self._contar_vigilancias(estado)

        # Forward checking de vigilâncias totais restantes.
        vigilancias_restantes = sum(
            self.max_vigilancias_docente - contagens[d]
            for d in self.docentes
        )
        restantes_indices = [
            i for i in self.ordem_disciplinas
            if i != indice and estado.atribuicoes[i] is None
        ]
        min_vigilancias_futuras = sum(
            self._min_salas_disciplina[i] * self.vigilantes_por_sala
            for i in restantes_indices
        )

        if vigilancias_restantes < self._min_salas_disciplina[indice] * self.vigilantes_por_sala + min_vigilancias_futuras:
            return []

        # Pré-calcular ocupação por slot em uma única passagem.
        salas_ocupadas_slot = [set() for _ in range(self.num_slots)]
        docentes_ocupados_slot = [set() for _ in range(self.num_slots)]
        mask_slot = [0 for _ in range(self.num_slots)]

        for idx, atrib in enumerate(estado.atribuicoes):
            if atrib is not None:
                s = atrib.slot
                salas_ocupadas_slot[s].update(atrib.salas)
                docentes_ocupados_slot[s].update(atrib.vigilantes)
                mask_slot[s] |= (1 << idx)

        acoes_com_custo = []
        mask_indice = self._conflitos_mask[indice]

        for slot in range(self.num_slots):
            if (mask_slot[slot] & mask_indice) != 0:
                continue

            # Forward checking rápido: garantir que nenhuma disciplina futura fica sem slot livre.
            novo_mask_slot = mask_slot[slot] | (1 << indice)
            viavel = True
            for j in restantes_indices:
                mask_j = self._conflitos_mask[j]
                tem_slot = False
                for s2 in range(self.num_slots):
                    m = novo_mask_slot if s2 == slot else mask_slot[s2]
                    if (m & mask_j) == 0:
                        tem_slot = True
                        break
                if not tem_slot:
                    viavel = False
                    break
            if not viavel:
                continue

            salas_livres = [s for s in self.salas if s.id not in salas_ocupadas_slot[slot]]
            if not salas_livres:
                continue

            docentes_disponiveis = [
                d for d in self.docentes
                if d not in docentes_ocupados_slot[slot]
                and contagens[d] < self.max_vigilancias_docente
            ]

            melhor_desperdicio_1_sala = None

            # 1. Tentar combinações de 1 sala
            if (
                len(docentes_disponiveis) >= self.vigilantes_por_sala
                and vigilancias_restantes - self.vigilantes_por_sala >= min_vigilancias_futuras
            ):
                vig_1 = self._atribuicao_canonica_vigilantes(docentes_disponiveis, contagens, 1)
                for sala in salas_livres:
                    if sala.capacidade >= disciplina.inscritos:
                        desperdicio = sala.capacidade - disciplina.inscritos
                        if melhor_desperdicio_1_sala is None or desperdicio < melhor_desperdicio_1_sala:
                            melhor_desperdicio_1_sala = desperdicio

                        acao = Acao(
                            disciplina_indice=indice,
                            disciplina_id=disciplina.id,
                            slot=slot,
                            salas=(sala.id,),
                            vigilantes_por_sala=vig_1,
                        )
                        custo_est = self._custo_incremental_rapido(estado, indice, slot, sala.capacidade)
                        acoes_com_custo.append((custo_est, desperdicio, slot, acao))

            # 2. Tentar combinações de 2 salas (apenas se houver vigilantes suficientes
            #    e o desperdício for estritamente menor que qualquer opção de 1 sala já encontrada)
            vig_necessarias_2 = 2 * self.vigilantes_por_sala
            if (
                len(salas_livres) >= 2
                and len(docentes_disponiveis) >= vig_necessarias_2
                and vigilancias_restantes - vig_necessarias_2 >= min_vigilancias_futuras
            ):
                vig_2 = self._atribuicao_canonica_vigilantes(docentes_disponiveis, contagens, 2)
                for s1, s2 in combinations(salas_livres, 2):
                    capacidade = s1.capacidade + s2.capacidade
                    if capacidade < disciplina.inscritos:
                        continue
                    desperdicio = capacidade - disciplina.inscritos
                    if melhor_desperdicio_1_sala is not None and desperdicio >= melhor_desperdicio_1_sala:
                        continue

                    acao = Acao(
                        disciplina_indice=indice,
                        disciplina_id=disciplina.id,
                        slot=slot,
                        salas=(s1.id, s2.id),
                        vigilantes_por_sala=vig_2,
                    )
                    custo_est = self._custo_incremental_rapido(estado, indice, slot, capacidade)
                    acoes_com_custo.append((custo_est, desperdicio, slot, acao))

        acoes_com_custo.sort(key=lambda item: (item[0], item[1], item[2]))
        return [item[3] for item in acoes_com_custo]

    def _acao_valida(self, estado, acao):
        if not isinstance(acao, Acao):
            return False

        indice = acao.disciplina_indice
        if not 0 <= indice < self.num_disciplinas:
            return False
        if indice != self.proxima_disciplina(estado):
            return False
        if acao.disciplina_id != self.disciplinas[indice].id:
            return False
        if not 0 <= acao.slot < self.num_slots:
            return False
        if len(acao.salas) not in (1, 2) or len(set(acao.salas)) != len(acao.salas):
            return False
        if any(s not in self.salas_por_id for s in acao.salas):
            return False

        capacidade_total = sum(self.salas_por_id[s].capacidade for s in acao.salas)
        if capacidade_total < self.disciplinas[indice].inscritos:
            return False

        if any(s in self._salas_ocupadas(estado, acao.slot) for s in acao.salas):
            return False
        if self._tem_conflito_no_slot(estado, indice, acao.slot):
            return False

        if len(acao.vigilantes_por_sala) != len(acao.salas):
            return False
        for par in acao.vigilantes_por_sala:
            if len(par) != self.vigilantes_por_sala or len(set(par)) != len(par):
                return False

        todos_vigilantes = acao.vigilantes
        if len(todos_vigilantes) != len(set(todos_vigilantes)):
            return False
        if any(d not in self.docentes for d in todos_vigilantes):
            return False
        if any(d in self._docentes_ocupados_no_slot(estado, acao.slot) for d in todos_vigilantes):
            return False

        contagens = self._contar_vigilancias(estado)
        if any(contagens[d] + 1 > self.max_vigilancias_docente for d in todos_vigilantes):
            return False

        return True

    def resultado(self, estado, acao, validar=False):
        """Aplica uma acção ao estado atual."""
        if validar and not self._acao_valida(estado, acao):
            raise ValueError("Acção inválida: viola restrições rígidas.")

        novas = list(estado.atribuicoes)
        novas[acao.disciplina_indice] = acao
        return Estado(atribuicoes=tuple(novas))

    def custo(self, estado, acao, novo_estado, validar=False):
        """Calcula o custo incremental de uma acção."""
        if validar and not self._acao_valida(estado, acao):
            raise ValueError("Não é possível calcular o custo de uma acção inválida.")

        capacidade_total = sum(self.salas_por_id[s].capacidade for s in acao.salas)
        return self._custo_incremental_rapido(estado, acao.disciplina_indice, acao.slot, capacidade_total)

    def teste_objetivo(self, estado):
        return estado.completo and self.validar_estado(estado)

    def heuristica(self, estado, nome="h1"):
        """Integração com a interface comum Problema.heuristica(s, nome)."""
        from heuristicas import h0, h1, h2

        mapa = {"h0": h0, "h1": h1, "h2": h2}
        chave = nome.strip().lower()
        if chave not in mapa:
            raise ValueError(f"Heurística desconhecida: {nome}")
        return mapa[chave](estado, self)

    def validar_estado(self, estado):
        if not isinstance(estado, Estado) or len(estado.atribuicoes) != self.num_disciplinas:
            return False

        temporario = self.estado_inicial()
        encontrou_vazio = False
        for indice in self.ordem_disciplinas:
            acao = estado.atribuicoes[indice]
            if acao is None:
                encontrou_vazio = True
                continue
            if encontrou_vazio or not self._acao_valida(temporario, acao):
                return False
            novas = list(temporario.atribuicoes)
            novas[indice] = acao
            temporario = Estado(tuple(novas))
        return True

    def calcular_custo_total(self, estado):
        if not self.validar_estado(estado):
            raise ValueError("Estado inválido.")

        custo_total = 0.0
        atribuicoes = [a for a in estado.atribuicoes if a is not None]
        for i, acao in enumerate(atribuicoes):
            capacidade = sum(self.salas_por_id[s].capacidade for s in acao.salas)
            inscritos = self.disciplinas[acao.disciplina_indice].inscritos
            custo_total += (capacidade - inscritos) * self.penalizacao_lugar_vazio

            dia_atual = acao.slot // self.periodos_por_dia
            for anterior in atribuicoes[:i]:
                partilhados = self.matriz_partilhados[acao.disciplina_indice][anterior.disciplina_indice]
                if partilhados == 0:
                    continue
                diff = abs(dia_atual - (anterior.slot // self.periodos_por_dia))
                if diff == 0:
                    custo_total += partilhados * self.penalizacao_mesmo_dia
                elif diff == 1:
                    custo_total += partilhados * self.penalizacao_dias_consecutivos
        return custo_total

    def obter_dia(self, slot):
        return slot // self.periodos_por_dia

    def obter_periodo(self, slot):
        return slot % self.periodos_por_dia

    def nome_dia(self, slot):
        dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira"]
        dia = self.obter_dia(slot)
        return dias_semana[dia] if dia < len(dias_semana) else f"Dia {dia + 1}"

    def nome_periodo(self, slot):
        periodo = self.obter_periodo(slot)
        if periodo == 0:
            return "Manhã"
        if periodo == 1:
            return "Tarde"
        return f"Período {periodo + 1}"

    def solucao_para_tabela(self, estado):
        if not self.validar_estado(estado):
            raise ValueError("O estado não representa um calendário válido.")
        tabela = []
        for acao in estado.atribuicoes:
            if acao is None:
                continue
            disciplina = self.disciplinas[acao.disciplina_indice]
            for indice_sala, sala_id in enumerate(acao.salas):
                tabela.append({
                    "disciplina": disciplina.nome,
                    "disciplina_id": disciplina.id,
                    "dia": self.nome_dia(acao.slot),
                    "periodo": self.nome_periodo(acao.slot),
                    "slot": acao.slot,
                    "sala": sala_id,
                    "capacidade": self.salas_por_id[sala_id].capacidade,
                    "vigilantes": list(acao.vigilantes_por_sala[indice_sala]),
                })
        return sorted(tabela, key=lambda item: (item["slot"], item["sala"]))

    def mostrar_estado(self, estado):
        print("\n========================================")
        print("CALENDÁRIO DE EXAMES")
        print("========================================")
        for acao in sorted(
            [a for a in estado.atribuicoes if a is not None],
            key=lambda a: (a.slot, a.disciplina_id),
        ):
            disciplina = self.disciplinas[acao.disciplina_indice]
            print(f"\nDisciplina: {disciplina.nome}")
            print(f"Dia: {self.nome_dia(acao.slot)} | Período: {self.nome_periodo(acao.slot)} (Slot {acao.slot})")
            print(f"Salas: {', '.join(acao.salas)}")
            for sala, vigilantes in zip(acao.salas, acao.vigilantes_por_sala):
                print(f"  {sala}: {', '.join(vigilantes)}")
        print("\n========================================")
        print(f"Disciplinas marcadas: {estado.disciplinas_marcadas}/{self.num_disciplinas}")
        if estado.completo:
            print(f"Custo total: {self.calcular_custo_total(estado):.2f}")
        print("========================================")