# Construction Budget MVP — Canonical Model v0.2

## 1. Scope

O modelo representa a formação de um orçamento de execução a partir de:

1. requisitos de um projeto;
2. serviços mensuráveis;
3. composições de insumos;
4. observações contextuais de preços;
5. custos de nível da obra;
6. parâmetros de formação do preço, incluindo BDI.

O modelo canônico é independente de SINAPI, SICRO ou qualquer outra fonte específica. Cada fonte externa deve ser traduzida para esta estrutura por um adapter.

---

# 2. Fundamental Flow

\[
Project
\rightarrow
ServiceRequirements
\rightarrow
Services/Compositions
\rightarrow
Inputs
\rightarrow
UnitCosts
\rightarrow
BudgetItems
\]

\[
BudgetItems
+
ProjectLevelCosts
\rightarrow
CostOfWork
\xrightarrow{BDI}
SellingPrice
\]

O projeto determina **o que deve ser executado**.

O orçamento determina **quanto custa executar o que foi determinado**.

---

# 3. Project

Representa o conjunto de requisitos técnicos que antecede o orçamento.

O projeto pode determinar:

- objeto a executar;
- especificações;
- métodos;
- quantitativos;
- condições técnicas;
- serviços necessários.

O projeto não contém, por definição, seu custo.

## Relation

\[
Project \rightarrow \{ServiceRequirement_1,\ldots,ServiceRequirement_n\}
\]

---

# 4. Service / Composition

No âmbito do projeto, `Service` é uma atividade ou resultado técnico mensurável.

No âmbito do orçamento, o mesmo serviço é representado por uma **composição de custos**, que determina quais recursos são necessários para produzir uma unidade desse serviço.

As duas representações são consideradas faces operacionais do mesmo objeto.

## Minimal Structure

```text
Service
- id
- external_id?
- description
- specification?
- unit
- category?
- reference_source?
- composition
```

## Composition

Uma composição é um conjunto plano:

\[
S_j=\{(I_i,k_{ij})\}
\]

onde:

- \(I_i\) = insumo;
- \(k_{ij}\) = coeficiente de consumo do insumo \(i\) para uma unidade do serviço \(j\).

Dimensionalmente:

\[
[k_{ij}]
=
\frac{U_i}{U_j}
\]

Exemplo:

\[
0,50\frac{h_{pedreiro}}{m^2_{alvenaria}}
\]

---

# 5. Flat Composition Invariant

O modelo canônico **não utiliza composições recursivas**.

Caso uma fonte externa represente:

```text
Service A
 └── Auxiliary Composition B
       ├── Input X
       └── Input Y
```

o adapter deve expandir:

```text
Service A
├── Input X × adjusted coefficient
└── Input Y × adjusted coefficient
```

A transformação é válida devido à linearidade:

\[
A=a_1x_1+\alpha B
\]

\[
B=b_1x_2+b_2x_3
\]

portanto:

\[
A=a_1x_1+\alpha b_1x_2+\alpha b_2x_3
\]

A hierarquia original pode ser preservada como provenance, mas não participa do cálculo canônico.

---

# 6. Input

`Input` representa um recurso economicamente consumido na execução de um serviço.

Categorias canônicas iniciais:

```text
material
labor
equipment
subcontracted_service
```

A taxonomia específica de uma fonte não redefine essas categorias.

## Minimal Structure

```text
Input
- id
- source_identity
- description
- technical_family?
- canonical_type
- source_type?
- unit
- cost_regime?
- normalized_specification?
```

---

# 7. Cost Regime

Objetos tecnicamente semelhantes podem constituir insumos economicamente distintos.

Exemplo:

```text
Betoneira 400 L
├── rental
├── purchase
└── owned_operation
```

Aquisição e locação não devem ser colapsadas porque possuem mecanismos de custo diferentes.

Portanto:

\[
TechnicalIdentity \neq BudgetIdentity
\]

quando o regime econômico é diferente.

---

# 8. Labor

Mão de obra é tratada como um `Input`, mas seu custo pode ser construído a partir de componentes.

Exemplo conceitual:

\[
C_{labor} = W + ES + EC
\]

onde:

- \(W\) = remuneração-base;
- \(ES\) = encargos sociais/trabalhistas;
- \(EC\) = custos complementares.

Custos complementares podem incluir, conforme a metodologia utilizada:

- alimentação;
- transporte;
- EPI;
- ferramentas;
- seguros;
- exames;
- capacitação.

Esses elementos não precisam ser classificados como insumos canônicos independentes apenas porque determinada fonte os representa dessa maneira.

Regimes de contratação ou obtenção de mão de obra devem permanecer explícitos.

Um serviço terceirizado não é simplesmente “mão de obra com outro encargo”; é um `subcontracted_service` cujo fornecedor internaliza sua própria estrutura de custos.

---

# 9. PriceObservation

Preço não é atributo intrínseco do insumo.

É uma observação contextual.

## Structure

```text
PriceObservation
- input_id
- value
- currency
- unit
- supplier?
- reference_source
- location
- reference_period
- cost_regime
- labor_regime?
- evidence_type?
- status
- provenance?
- conditions?
```

Formalmente:

\[
p_i=p_i(E)
\]

onde \(E\) representa o contexto econômico.

---

# 10. Supplier and ReferenceSource

São conceitos distintos.

## Supplier

Entidade da qual o recurso pode efetivamente ser adquirido, contratado ou alugado.

Exemplos:

- fabricante;
- revendedor;
- locadora;
- prestador de serviços.

Pode também ser uma entidade fictícia em datasets didáticos, desde que essa convenção seja explicitamente documentada.

## ReferenceSource

Origem epistemológica da observação.

Exemplos:

```text
SINAPI
SICRO
supplier quotation
historical company data
custom dataset
```

Assim:

```text
supplier = SINAPI_MATERIAL_A
reference_source = SINAPI
```

é aceitável em um PoC, desde que `SINAPI_MATERIAL_A` seja identificado como fornecedor virtual.

---

# 11. Price Evidence and Provenance

Uma observação de preço deve permitir distinguir:

- cotação real;
- preço referencial;
- valor regional;
- média;
- valor inferido;
- fallback;
- valor sintético;
- ausência de valor.

Invariante:

\[
missing \neq 0
\]

Preço desconhecido nunca pode ser convertido silenciosamente para zero.

---

# 12. Price Family

Uma fonte pode organizar insumos em famílias de preços.

Cada família possui um membro representativo normalizado:

\[
\rho_r=1
\]

e membros relacionados:

\[
p_i=\rho_i p_r
\]

## Structure

```text
PriceFamily
- id
- representative_input

PriceFamilyMember
- family_id
- input_id
- representation_coefficient
```

O coeficiente não existe isoladamente: é uma relação do membro com o representante da família.

---

# 13. Input Identity and Equivalence

Registros provenientes de fontes distintas nunca perdem sua identidade de origem.

Assim:

```text
SINAPI:1234
SICRO:9876
```

continuam sendo dois registros distintos.

Entretanto, eles podem ser equivalentes para determinada operação.

## InputEquivalence

```text
InputEquivalence
- input_a
- input_b
- relation
- justification?
```

Estados iniciais:

```text
exact
compatible
non_equivalent
unknown
```

Não será utilizado score contínuo no PoC.

Equivalência:

\[
A\sim B
\]

não implica:

\[
A=B
\]

---

# 14. Price Selection Policy

O sistema não determina autonomamente qual fonte possui o preço “verdadeiro”.

Ele executa uma política explícita.

Critérios possíveis:

1. compatibilidade técnica;
2. regime econômico;
3. localização;
4. período de referência;
5. qualidade/tipo da evidência;
6. fonte preferencial;
7. fallback autorizado.

Exemplo:

```text
Primary source: SINAPI
Location: SC
Reference period: 09/2026

1. exact local observation
2. compatible regional observation
3. regional average
4. national average
5. authorized alternative source
6. unresolved
```

Qualquer fallback deve permanecer rastreável.

---

# 15. Geographic Fallback

Não existe fallback geográfico universal.

A política inicial do modelo pode considerar:

```text
exact location
→ compatible regional value
→ regional average
→ national average
→ explicitly configured source fallback
→ unresolved
```

Valores substituídos devem carregar sua origem.

O sistema deve ser capaz de informar, por exemplo:

```text
82% exact/local
12% regional
6% national fallback
```

---

# 16. Unit Cost

O custo unitário do serviço é:

\[
c_j(E)=\sum_i k_{ij}p_i(E)
\]

Dimensionalmente:

\[
\frac{U_i}{U_j}
\times
\frac{R\$}{U_i}
=
\frac{R\$}{U_j}
\]

`UnitCost` é inicialmente considerado **dado derivado**, não entidade independente obrigatoriamente persistida.

---

# 17. ServiceRequirement

Representa um serviço exigido pelo projeto.

```text
ServiceRequirement
- project_id
- service_id
- quantity
- specification_override?
```

Formalmente:

\[
R_j=(S_j,Q_j)
\]

---

# 18. BudgetItem

Um `BudgetItem` é a ocorrência valorizada de um `ServiceRequirement`.

Não representa uma nova espécie de serviço.

\[
BudgetItem = ServiceRequirement + EconomicContext
\]

Seu custo é:

\[
C_j=Q_jc_j
\]

O modelo v0.2 não determina ainda quanto do raciocínio intermediário deve ser persistido dentro do item.

Essa é uma decisão futura de infraestrutura entre:

- menor redundância;
- maior rastreabilidade;
- maior velocidade de recuperação.

---

# 19. Project-Level Costs

Existem custos atribuíveis à obra, mas não naturalmente distribuídos por unidade de um serviço produtivo.

Exemplos:

- mobilização;
- desmobilização;
- canteiro;
- administração local.

Eles devem permanecer separados das composições produtivas.

```text
ProjectLevelCost
- description
- value or calculation rule
- cost_driver?
- supplier?
- provenance?
```

Então:

\[
C_{work} = \sum_jC_j + \sum_kP_k
\]

---

# 20. BDI

BDI atua como mecanismo de **formação do preço**, não como composição produtiva.

Simplificadamente:

\[
SellingPrice
=
CostOfWork(1+BDI)
\]

A composição interna do BDI pode conter:

- administração central;
- seguros;
- garantias;
- riscos;
- despesas financeiras;
- remuneração pretendida;
- tributos sobre faturamento.

As parcelas possuem bases de incidência potencialmente diferentes.

Portanto, BDI não deve ser interpretado como simples soma arbitrária de percentuais.

A remuneração incluída no BDI não é lucro realizado.

\[
ExpectedRemuneration\neq RealizedProfit
\]

---

# 21. Budget

```text
Budget
- project
- economic_context
- selection_policy
- budget_items[]
- project_level_costs[]
- BDI
- cost_of_work
- selling_price
```

Formalmente:

\[
Budget
=
\sum BudgetItems
+
ProjectLevelCosts
+
PriceFormation
\]

---

# 22. Data Classification

## Primarily stored

```text
Project
Service
Composition coefficients
Input
PriceObservation
Supplier
ReferenceSource
PriceFamily
InputEquivalence
SelectionPolicy
ProjectLevelCost
BDI parameters
```

## Primarily derived

```text
selected input price
service unit cost
budget item cost
cost of work
BDI effective rate
selling price
fallback statistics
```

A decisão final sobre cache/persistência desses resultados fica para uma etapa posterior.

---

# 23. Canonical Invariants

O PoC v0.1 deverá respeitar:

1. **Project ≠ Budget.**
2. O projeto antecede economicamente o orçamento.
3. Serviço e composição são duas representações do mesmo objeto no âmbito deste MVP.
4. Uma composição canônica é plana.
5. Toda composição relaciona `Input × coefficient`.
6. Coeficientes possuem significado dimensional explícito.
7. Preço não é propriedade permanente do insumo.
8. Toda observação de preço possui contexto.
9. `Supplier ≠ ReferenceSource`.
10. `missing ≠ zero`.
11. Regimes econômicos distintos não devem ser colapsados.
12. Identidade entre fontes é preservada.
13. Equivalência não implica identidade.
14. Substituição de preço nunca é silenciosa.
15. Seleção de preço é determinada por política explícita.
16. Custos de nível da obra permanecem separados das composições produtivas.
17. BDI atua após a formação do custo da obra.
18. Dados específicos de uma fonte não modificam automaticamente a ontologia canônica.

---

# 24. Source Adapter Contract

Cada adapter deve realizar:

```text
External Source
      ↓
parse
      ↓
normalize terminology
      ↓
normalize units
      ↓
resolve source-specific structures
      ↓
flatten auxiliary compositions
      ↓
preserve provenance
      ↓
Canonical Model
```

O motor orçamentário não deve saber se os dados vieram de:

```text
SINAPI
SICRO
custom CSV
supplier quotation
future source
```

---

# 25. Explicitly Deferred Decisions

Não fazem parte do v0.2:

- SQL versus Parquet;
- DuckDB;
- arquitetura de classes definitiva;
- interface gráfica;
- dashboard;
- integração web;
- persistência de resultados intermediários;
- score quantitativo de equivalência;
- algoritmo sofisticado de matching entre fontes;
- cálculo completo de folha de pagamento;
- tributação empresarial completa;
- DRE;
- cronograma físico-financeiro;
- atualização automática de bases;
- modelagem completa da documentação técnica SINAPI.

---

# 26. PoC v0.1 Acceptance Test

O primeiro PoC em Python deve conseguir representar um dataset pequeno contendo:

- 5–10 insumos;
- múltiplos tipos de insumo;
- ao menos um equipamento com regime econômico explícito;
- mão de obra com encargos;
- duas fontes;
- fornecedores;
- duas observações equivalentes de preço;
- um caso `compatible`;
- um preço ausente;
- 2–3 serviços;
- composições planas;
- um custo de nível da obra;
- BDI parametrizado.

E deve calcular:

\[
PriceSelection
\rightarrow
UnitCost
\rightarrow
BudgetItemCost
\rightarrow
CostOfWork
\rightarrow
SellingPrice
\]

mantendo explicável a procedência de cada valor escolhido.

---

# 27. Status

**Canonical Model v0.2: conceptually frozen for PoC v0.1.**

Mudanças posteriores devem decorrer de:

- contradições encontradas na implementação;
- dados reais impossíveis de representar;
- requisitos comerciais concretos;

e não apenas de preferência arquitetural.