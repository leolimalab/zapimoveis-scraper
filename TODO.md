# Próximos Passos - ZapImóveis Scraper

## 1. Aumentar Resultados da Pesquisa (+100)
- [ ] Resolver problema de paginação (página 2+ não retorna dados)
- [ ] Investigar se há limite da API ou proteção anti-bot
- [ ] Implementar scroll infinito ou navegação por páginas
- [ ] Configurar `MAX_ITEMS` para valores maiores (200, 500, etc.)

## 2. Incluir Número da Rua
- [ ] Melhorar extração do endereço nas páginas de detalhe
- [ ] Usar regex mais preciso para separar rua e número
- [ ] Buscar seletor específico para número no DOM
- [ ] Fallback: extrair do campo `streetAddress` do schema.org

## 3. Busca por Termo Específico
- [ ] Adicionar parâmetro `--termo` ou `--busca` no CLI
- [ ] Implementar busca por:
  - Rua específica (ex: "Rua Gustavo Sampaio")
  - Avenida (ex: "Av. Atlântica")
  - Bairro (ex: "Leme", "Copacabana")
- [ ] Modificar URL de busca para incluir termo
- [ ] Filtrar resultados pós-extração quando necessário

## 4. Filtros para o Usuário

### 4.1 Filtro por Tamanho (m²)
- [ ] Adicionar parâmetro `--tamanho-min` (ex: `--tamanho-min 70`)
- [ ] Adicionar parâmetro `--tamanho-max` (ex: `--tamanho-max 150`)
- [ ] Aplicar filtro durante extração ou pós-processamento

### 4.2 Filtro por Preço
- [ ] Adicionar parâmetro `--preco-min` (ex: `--preco-min 500000`)
- [ ] Adicionar parâmetro `--preco-max` (ex: `--preco-max 1000000`)
- [ ] Suportar formato brasileiro (1.000.000) e numérico (1000000)

### 4.3 Preço por m² (Campo Calculado)
- [ ] Adicionar campo `preco_m2` no modelo Property
- [ ] Cálculo: `preco_m2 = preco / tamanho_m2`
- [ ] Incluir no CSV e JSON de saída
- [ ] Adicionar filtro `--preco-m2-max` (ex: `--preco-m2-max 15000`)

## Estrutura Proposta para CLI

```bash
# Exemplos de uso futuro:

# Busca com filtros
python main.py --tamanho-min 70 --preco-max 1000000

# Busca por rua específica
python main.py --busca "Rua Gustavo Sampaio"

# Busca com múltiplos filtros
python main.py --busca "Av. Atlântica" --tamanho-min 100 --preco-max 2000000

# Ordenar por preço/m²
python main.py --ordenar preco_m2

# Limitar resultados
python main.py --limite 200
```

## Prioridade Sugerida

1. **Alta**: Preço por m² (campo calculado simples)
2. **Alta**: Filtros de preço e tamanho
3. **Média**: Busca por termo específico
4. **Média**: Aumentar limite de resultados
5. **Baixa**: Número da rua (depende da disponibilidade no site)

---
*Última atualização: 30/01/2026*
