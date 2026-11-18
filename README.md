# Projecto de Inteligência Artificial — P4: Calendário de Exames

## 1. Visão geral

Este projecto resolve o problema de escalonamento de exames da Faculdade de Engenharia, designado como P4, usando técnicas de busca em inteligência artificial. A ideia central é representar cada solução possível como um estado do problema e expandir esse espaço de estados com algoritmos de busca até encontrar um calendário válido e, idealmente, de menor custo.

O projecto trabalha com:

- busca não informada: BFS, DFS, IDS, UCS
- busca informada: Gulosa, A*, DFBnB
- heurísticas admissíveis para estimar o custo restante
- geração automática de instâncias de diferentes tamanhos
- execução de experiências comparativas e exportação dos resultados em CSV

O grupo é o 04 (turno laboral) e a semente oficial é `202604`.

---

## 2. Descrição do problema

O objectivo é atribuir cada disciplina a um slot do calendário, respeitando as restrições do problema e minimizando o custo global. O custo não é apenas a viabilidade da solução, mas também a qualidade do calendário.

### 2.1. Estrutura do calendário

- 5 dias por semana
- 2 períodos por dia: manhã e tarde
- total de 10 slots temporais
- 4 salas com capacidades diferentes: 40, 60, 80 e 120 lugares
- cada exame pode ocupar 1 ou 2 salas, dependendo do número de inscritos
- cada sala exige 2 vigilantes
- há 8 docentes disponíveis
- cada docente pode fazer no máximo 1 vigilância por período e no máximo 4 vigilâncias na semana

### 2.2. Restrições

- exames com estudantes em comum não podem ocorrer no mesmo slot
- não pode haver conflitos de vigilância
- a capacidade das salas deve ser suficiente para o número de inscritos
- a solução deve atribuir todas as disciplinas ao calendário

### 2.3. Função de custo

A função de custo penaliza soluções menos desejáveis:

- `+3.00` por estudante com dois exames no mesmo dia
- `+1.00` por estudante com dois exames em dias consecutivos
- `+0.01` por lugar vazio nas salas atribuídas

Assim, a solução óptima é a que minimiza a penalização global, não apenas a ordem de atribuição.

---

## 3. Estrutura do repositório

```text
projecto_ia_grupo04/
├── problema.py          # Classe abstracta base para problemas de busca
├── dominio.py           # Formulação do calendário de exames
├── buscas.py            # Implementação dos 7 algoritmos de pesquisa
├── heuristicas.py       # Heurísticas h0, h1, h2 e validações
├── gerador.py           # Geração de instâncias de teste em JSON
├── experiencias.py      # Execução de testes comparativos e gráficos
├── main.py              # Menu interativo em terminal
├── instancias/          # Instâncias por nível (pequena, media, grande)
├── resultados/          # CSV e gráficos gerados
├── tests/               # Casos de teste automatizados (pytest)
│   ├── conftest.py
│   ├── test_problema.py
│   ├── test_dominio.py
│   ├── test_buscas.py
│   └── test_heuristicas.py
├── requirements.txt     # Dependências do projecto
├── README.md            # Documentação do projecto
└── .
```

---

## 4. Como o código representa o problema

### 4.1. Módulo `problema.py`

Este ficheiro define a base genérica para qualquer problema de busca em IA.

Contém:

- `Problema`: classe abstracta base
- `No`: representação de um nó da árvore de pesquisa
- `caminho(no)`: função auxiliar para reconstruir a sequência de estados/ações

A classe `Problema` exige que cada problema concreto implemente:

- `acoes(estado)`: ações possíveis
- `resultado(estado, acao)`: aplicação da ação ao estado
- `custo(estado, acao, novo_estado)`: custo da transição
- `teste_objetivo(estado)`: verifica se a solução está completa

O `No` guarda:

- o `estado`
- o nó pai
- a ação que originou o nó
- o custo acumulado
- a profundidade

Isto permite reconstruir a solução final a partir do nó objetivo.

### 4.2. Módulo `dominio.py`

É o núcleo do projecto. Aqui é formulado o problema real: `CalendarioExames`.

#### Estruturas principais

- `Disciplina`: identifica uma disciplina com `id`, `nome` e `inscritos`
- `Sala`: representa uma sala com `id` e `capacidade`
- `Acao`: representa uma atribuição de uma disciplina a um slot e salas.
- `Estado`: guarda o calendário parcial em forma imutável de tuplas

O `Estado` é um estado parcial do calendário, onde cada posição do vetor representa uma disciplina e contém:

- `None` se ainda não foi agendada
- `Acao(...)` se já foi atribuída

Isto é uma representação muito útil para a busca porque permite:

- comparar estados facilmente
- utilizar hashing para evitar ciclos e estados repetidos
- verificar se o calendário está completo

#### Dados e validações

Ao criar um `CalendarioExames`, o código carrega a instância em JSON e valida:

- número de disciplinas
- número de slots (`dias × periodos_por_dia`)
- consistência da matriz de estudantes partilhados
- existência de IDs únicos
- capacidade mínima das salas
- limite de vigilância

Também se calculam estruturas auxiliares para acelerar as pesquisas, como:

- ordem das disciplinas por restrição
- máscara de conflitos entre disciplinas
- mínimo de salas exigidas por disciplina

#### Heurística de ordenação de disciplinas

A função `_calcular_ordem_disciplinas()` ordena as disciplinas mais restritas primeiro. A ordem privilegiada é:

1. disciplinas que exigem 2 salas
2. maior grau de conflito
3. maior número total de estudantes partilhados
4. maior número de inscritos

Este truque reduz significativamente o espaço de busca porque tentamos preencher primeiro as disciplinas mais difíceis.

#### Funções de apoio

A classe também implementa funções como:

- `proxima_disciplina(estado)`: devolve a próxima disciplina por marcar
- `_salas_ocupadas(estado, slot)`: salas já ocupadas num slot
- `_docentes_ocupados_no_slot(estado, slot)`: docentes já comprometidos
- `_tem_conflito_no_slot(...)`: detecta conflito rígido

Estas funções são essenciais para gerar apenas ações válidas.

---

## 5. Como são geradas as ações e os sucessores

A parte central da expansão do estado está em `CalendarioExames.acoes(estado)` e em `resultado(estado, acao)`.

### 5.1. Geração de ações possíveis

A função de ações percorre as disciplinas ainda não agendadas e tenta colocá-las em slots válidos. Para cada disciplina, considera:

- slot disponível sem conflito rígido
- número de salas necessárias
- capacidade das salas
- vigilância dos docentes
- limite máximo de vigilâncias por docente

Se uma disciplina não pode ser colocada em certo slot, essa ação é ignorada.

### 5.2. Atribuição de salas e vigilantes

Cada ação contém:

- `disciplina_indice`
- `disciplina_id`
- `slot`
- `salas`
- `vigilantes_por_sala`

A seleção dos vigilantes é feita de forma canónica, isto é, de modo a:

- respeitar o número mínimo necessário
- preferir docentes com menos vigilâncias acumuladas
- reduzir a ramificação e evitar simetrias redundantes

A lógica está documentada no comentário da função `_atribuicao_canonica_vigilantes()` e é uma otimização importante do projecto.

### 5.3. Custo de transição

A função `custo(...)` calcula o custo incremental da ação, que inclui:

- penalização por conflitos com disciplinas já marcadas no mesmo dia
- penalização por conflitos em dias consecutivos
- penalização por desperdício de lugares

Como o problema é formulado como minimização de custo, os algoritmos trabalham com custos acumulados em cada nó.

---

## 6. Busca em espaço de estados

### 6.1. Módulo `buscas.py`

Este ficheiro concentra a lógica de todos os algoritmos de pesquisa.

Existem 7 algoritmos implementados:

1. `BFS` — Breadth-First Search
2. `DFS` — Depth-First Search
3. `IDS` — Iterative Deepening Search
4. `UCS` — Uniform Cost Search
5. `Gulosa` — Greedy Best-First Search
6. `A*` — A estrela
7. `DFBnB` — Depth-First Branch and Bound

Todos seguem uma interface comum baseada em:

- `No` da árvore de pesquisa
- `_gerar_filhos(...)`
- `_verificar_limites(...)`
- `_executar_com_metricas(...)`

#### Estrutura geral

Cada algoritmo cria um nó inicial e, iterativamente:

- expande o nó atual
- gera filhos
- valida objetivos e custos
- mantém a fronteira adequada ao algoritmo

A estrutura `ResultadoBusca` regista métricas como:

- custo da solução
- caminho encontrado
- número de nós expandidos
- número de nós gerados
- tamanho máximo da fronteira
- tempo de execução
- memória de pico
- sucesso/fracasso

#### Despachante

A função `executar_busca()` recebe:

- um problema
- o nome do algoritmo
- uma heurística opcional
- um estado inicial opcional
- limites de tempo e/ou expansões

e chama a implementação correta do algoritmo.

### 6.2. Diferentes estratégias

#### BFS

Explora por níveis. É útil para encontrar soluções em árvores pouco profundas e garante a primeira solução encontrada igual à mais curta em número de ações, embora não seja necessariamente a mais barata.

#### DFS

Explora um caminho até ao limite antes de retroceder. É mais leve em memória, mas pode ficar preso em ramos muito longos e não garante optimalidade.

#### IDS

Executa DFS com profundidade crescente. É um compromissio entre DFS e BFS, muito útil quando não se sabe a profundidade da solução.

#### UCS

Expande primeiro o nó com menor custo acumulado `g(n)`. É o algoritmo mais adequado para encontrar uma solução de custo mínimo quando não há heurística.

#### Gulosa

Escolhe sempre o nó com menor estimativa de custo restante `h(n)`, ignorando o custo já gasto. É rápido, mas pode conduzir a soluções subótimas.

#### A*

Usa `f(n) = g(n) + h(n)`. É geralmente mais eficiente que UCS quando a heurística é boa, porque combina custo acumulado com custo restante estimado.

#### DFBnB

Persegue uma solução por profundidade e usa um limite superior de custo para podar ramos que já superem a melhor solução conhecida. É uma estratégia de branch and bound adaptada a problemas de otimização.

---

## 7. Heurísticas

### 7.1. Módulo `heuristicas.py`

Este módulo contém as funções de estimação de custo restante.

#### `h0(estado, problema)`

Heurística nula, sempre igual a zero. Serve como referência para comparar a eficácia das heurísticas informadas.

#### `h1(estado, problema)`

Heurística admissível e consistente. Calcula:

- o desperdício mínimo de lugares para cada disciplina ainda não atribuída
- a penalização mínima inevitável contra disciplinas já marcadas
- soma tudo em um limite inferior do custo restante

A principal ideia é não exagerar a estimativa: só incluir uma cota inferior realista do custo que ainda terá de ser pago.

#### `h2(estado, problema)`

Heurística mais informada que h1. Considera também:

- salas livres em cada slot
- docentes disponíveis em cada slot
- capacidade de vigilância
- pares de disciplinas ainda não marcadas com conflitos e custos inevitáveis em dias iguais ou consecutivos

Em termos práticos, h2 é mais forte do que h1 porque inclui mais restrições reais do problema, reduzindo a largura da busca e melhorando a eficiência dos algoritmos informados.

#### Testes de admissibilidade

A biblioteca também possui funções para testar se uma heurística satisfaz `h(s) <= h*(s)` em estados pequenos, usando UCS como referência.

---

## 8. Geração de instâncias

### 8.1. Módulo `gerador.py`

Este ficheiro gera problemas em JSON com diferentes níveis de complexidade:

- `pequena`
- `media`
- `grande`

Cada instância contém:

- número de disciplinas
- número de salas
- número de docentes
- matriz de estudantes partilhados
- capacidades das salas
- regras do problema

A geração é determinística a partir da semente `202604`, o que garante reprodutibilidade.

#### Exemplo de uso

```bash
python gerador.py --seed 202604 --quantidade 10 --diretorio instancias
```

O código usa um gerador aleatório com uma seed, mas a estrutura das instâncias é construída de forma controlada para garantir que as soluções tenham sentido e que exista espaço para calendários viáveis.

---

## 9. Execução das experiências

### 9.1. Módulo `experiencias.py`

Este módulo automatiza testes comparativos dos algoritmos em seis instâncias:
três pequenas, duas médias e uma grande. Quando há mais ficheiros disponíveis,
são escolhidos por ordem alfabética dentro de cada nível. A experiência
registada neste projecto utiliza:

- `instancias/pequena/instancia_01.json`, `instancia_02.json` e `instancia_03.json`
- `instancias/media/instancia_01.json` e `instancia_02.json`
- `instancias/grande/instancia_01.json`

O fluxo é:

1. localizar os ficheiros JSON em `instancias/` e seleccionar 3 pequenas, 2 médias e 1 grande
2. carregar cada instância
3. construir um `CalendarioExames`
4. executar `UCS` como referência para obter custo ótimo
5. executar os restantes algoritmos
6. guardar os resultados em `resultados/resultados.csv`
7. gerar os três gráficos em `resultados/graficos/`:
   - `nos_expandidos_vs_tamanho.png`: nós expandidos vs. tamanho da instância, com escala logarítmica no eixo dos nós
   - `tempo_vs_tamanho.png`: tempo de execução vs. tamanho da instância
   - `custo_vs_otimo.png`: custo obtido vs. custo ótimo, com a diagonal de referência do UCS

#### Ficheiro produzido

- [`resultados/resultados.csv`](resultados/resultados.csv), com uma linha por algoritmo e instância, incluindo estado, custos, nós expandidos, tempo e memória.

#### Gráficos

- são guardados em `resultados/graficos/`
- comparam os algoritmos nas instâncias selecionadas

A função `executar_experiencia()` mede:

- tempo total
- memória de pico
- estado final (`SUCESSO`, `FALHOU`, `ERRO`)
- motivo de falha

Cada execução tem limite de 60 segundos e 2048 MB de memória alocada em Python
(medida com `tracemalloc`). Ao ultrapassar um limite, a pesquisa é interrompida
e a execução é registada como `FALHOU` no CSV, em vez de ser omitida.

Isto facilita a análise quantitativa dos algoritmos.

---

## 10. Interface principal

### 10.1. Módulo `main.py`

Este ficheiro oferece um menu interativo em terminal para o utilizador:

- carregar uma instância existente
- gerar uma nova instância
- executar uma pesquisa
- escolher algoritmos e heurísticas
- visualizar a estrutura da solução passo a passo

### 10.2. Fluxo típico

```bash
python main.py
```

Depois, o menu permite:

1. carregar instância existente
2. gerar nova instância por nível
3. escolher algoritmo
4. escolher heurística (`h1` ou `h2`) quando necessário
5. visualizar o calendário final

A função `visualizar_solucao()` lê as ações da solução e apresenta ao utilizador cada passo, indicando:

- disciplina
- dia
- período
- salas atribuídas
- vigilantes por sala

---

## 11. Como correr o projecto

### Instalar dependências

```bash
pip install -r requirements.txt
```

### Executar a aplicação principal

```bash
python main.py
```

### Executar testes

```bash
pytest
```

### Gerar instâncias automaticamente

```bash
python gerador.py
```

### Executar experiências comparativas

```bash
python experiencias.py
```

---

## 12. Como as partes se ligam na prática

O fluxo completo do projecto é o seguinte:

1. `gerador.py` gera instâncias em JSON
2. `main.py` ou `experiencias.py` carrega essas instâncias
3. `dominio.py` transforma os dados em um problema `CalendarioExames`
4. `buscas.py` gera e expande estados via algoritmos
5. `heuristicas.py` estima o custo restante para melhorar a eficiência
6. `resultado` devolve a solução completa e respetivas métricas
7. `main.py` mostra a solução ao utilizador ou `experiencias.py` exporta dados para estudo comparativo

Visto desta forma, o projecto não é apenas um “algoritmo isolado”; é uma arquitetura completa para modelar, resolver e avaliar problemas de busca em IA.

---

## 13. Observações importantes

- O projecto foi construído de forma modular, de modo que cada parte do problema tem uma responsabilidade clara.
- O modelo do domínio (`dominio.py`) é o que realmente “traduz” o enunciado do problema para a linguagem de pesquisa.
- As heurísticas são fundamentais para tornar A* e DFBnB competitivos face a algoritmos não informados.
- A resolução do problema de exames é combinatória e, por isso, o tamanho da fronteira e a utilização de heurísticas têm grande impacto no desempenho.

---

## 14. Conclusão

Este projecto implementa uma solução completa para o problema P4 usando métodos de inteligência artificial clássica. O foco principal está na modelação rigorosa do problema, na criação de uma base genérica de busca e na comparação de diversas estratégias de exploração do espaço de estados.

A combinação de:

- representação explícita do estado
- geração de ações válidas
- custos bem definidos
- heurísticas informadas
- vários algoritmos de pesquisa

faz com que o código seja um exemplo muito útil de resolução de problemas de otimização combinatória com IA.
