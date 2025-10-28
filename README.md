# MySQL Stress Test

Ferramenta de teste de stress multi-threaded para MySQL usando queries extraídas de logs reais.

## ⚡ Início Rápido

```bash
# 0. Criar um ambiente isolado
virtualenv -p 3.12 .venv
source .venv/bin/activate

# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar credenciais
cp .env.example .env
# Editar .env com suas credenciais MySQL

# 3. Executar teste simples (usando queries já extraídas)
python mysql_stress_test.py -t 5 -d 30 -f queries.sql

# OU usar interface interativa
./exemplo_uso.sh
```

**Resultado esperado:** Relatório detalhado com estatísticas de performance, queries/segundo, tempos de resposta e análise de erros.

## 📋 Características Principais

- **🚀 Multi-threaded**: Suporte a múltiplas conexões concorrentes
- **⚙️ Flexível**: Execução por tempo ou número de queries
- **🤖 Extração automática**: Extrai queries válidas dos logs do MySQL
- **💫 Filtro avançado**: Remove automaticamente queries de sistema e monitoramento
- **🎨 Classificação inteligente**: Separa queries por tipo (read/write)
- **📈 Relatórios detalhados**: Estatísticas completas de performance
- **🔁 Retry automático**: Tentativas automáticas em caso de falha
- **📁 Logging completo**: Logs detalhados para análise

## 📁 Arquivos do Projeto

| Arquivo | Descrição | Uso |
|---------|-------------|-----|
| `requirements.txt` | 📦 Dependências Python | `pip install -r requirements.txt` |
| `extract_queries.py` | 📋 Extrator de queries do log MySQL | `python extract_queries.py log.sql -o queries.sql` |
| `teste_filtro_sistema.py` | 🔍 Analisador de efetividade do filtro | `python teste_filtro_sistema.py log.sql` |
| `exemplo_uso.sh` | 🚀 Interface interativa para testes | `./exemplo_uso.sh` |
| `.env.example` | 🔑 Template de configuração | `cp .env.example .env` |
| `mysql_stress_test.py` | 🎯 Script principal de stress test | `python mysql_stress_test.py -t 10 -d 60 -f queries.sql` |

## 🛠️ Instalação

1. **Clone ou copie os arquivos para o diretório desejado**

2. **Instale as dependências Python:**
```bash
pip install -r requirements.txt
```

3. **Configure as credenciais do banco:**
```bash
cp .env.example .env
# Edite o arquivo .env com suas credenciais
```

## ⚙️ Configuração

Edite o arquivo `.env` com suas configurações:

```env
# Configurações de conexão com MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=seu_usuario
MYSQL_PASSWORD=sua_senha
MYSQL_DATABASE=sua_base_dados

# Configurações do teste de stress
DEFAULT_THREADS=10
QUERY_TIMEOUT=30
CONNECTION_TIMEOUT=10
MAX_RETRIES=3

# Configurações de log
LOG_LEVEL=INFO
LOG_FILE=stress_test.log
```

## 🚀 Uso

### Extração de Queries (Primeira vez)

Se você tem um arquivo de log do MySQL, primeiro extraia as queries:

```bash
# Extração básica com filtros automáticos
python extract_queries.py /caminho/para/general.log -o queries.sql -m 5000

# Extração apenas queries de leitura
python extract_queries.py /caminho/para/general.log -o queries_read.sql -m 5000 -t read

# Extração apenas queries de escrita  
python extract_queries.py /caminho/para/general.log -o queries_write.sql -m 5000 -t write
```

**Parâmetros:**
- `/caminho/para/general.log`: Arquivo de log do MySQL
- `-o queries.sql`: Arquivo de saída com queries extraídas
- `-m 5000`: Máximo de queries para extrair (opcional)
- `-t read`: Extrair apenas queries de leitura (SELECT)
- `-t write`: Extrair apenas queries de escrita (INSERT/UPDATE/DELETE)

### Execução do Teste de Stress

#### 1. Teste por duração (recomendado):
```bash
python mysql_stress_test.py -t 10 -d 60
```
- `-t 10`: 10 threads concorrentes
- `-d 60`: Executa por 60 segundos

#### 2. Teste por número de queries:
```bash
python mysql_stress_test.py -t 5 -q 1000
```
- `-t 5`: 5 threads concorrentes  
- `-q 1000`: 1000 queries por thread

#### 3. Extração + Teste em uma única execução:
```bash
python mysql_stress_test.py -t 10 -d 30 --extract-queries --log-file ../general_all.log
```

### Parâmetros Completos

```
-t, --threads           Número de threads (conexões concorrentes) [OBRIGATÓRIO]
-q, --queries           Número de queries por thread
-d, --duration          Duração do teste em segundos (padrão: 60)
-f, --queries-file      Arquivo com queries SQL (padrão: queries.sql)
--extract-queries       Extrai queries do log antes de executar o teste
--log-file              Arquivo de log do MySQL para extração
--max-queries-extract   Máximo de queries para extrair (padrão: 5000)
--query-type            Filtrar queries por tipo ao extrair (read/write)
```

## 📊 Exemplos de Uso

### Teste rápido com 5 threads por 30 segundos:
```bash
python mysql_stress_test.py -t 5 -d 30
```

### Teste intenso com 20 threads por 2 minutos:
```bash
python mysql_stress_test.py -t 20 -d 120
```

### Teste específico com 500 queries por thread:
```bash
python mysql_stress_test.py -t 8 -q 500
```

### Extrair queries e testar imediatamente:
```bash
python mysql_stress_test.py -t 10 -d 60 --extract-queries --log-file ../general_all.log --max-queries-extract 2000
```

### Teste apenas com queries de leitura (SELECT):
```bash
# Extrai apenas queries de leitura
python extract_queries.py /caminho/log.sql -o queries_read.sql -t read
# Executa teste com queries de leitura
python mysql_stress_test.py -t 10 -d 60 -f queries_read.sql
```

### Teste apenas com queries de escrita (INSERT/UPDATE/DELETE):
```bash
# Extrai apenas queries de escrita
python extract_queries.py /caminho/log.sql -o queries_write.sql -t write
# Executa teste com queries de escrita (menos threads para evitar locks)
python mysql_stress_test.py -t 5 -d 30 -f queries_write.sql
```

## 🔍 Tipos de Queries

O script suporta filtrar queries por tipo para testes mais específicos:

### 📆 Queries de Leitura (`read`)
- **Incluem**: SELECT, SHOW, DESCRIBE, DESC, EXPLAIN, ANALYZE
- **Casos de uso**: 
  - Testar performance de consultas
  - Simular carga de usuários navegando
  - Verificar índices e otimizações
- **Vantagens**: Não modificam dados, seguro para produção
- **Recomendação**: Use mais threads (10-50)

### ✍️ Queries de Escrita (`write`)
- **Incluem**: INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, TRUNCATE, REPLACE
- **Casos de uso**:
  - Testar locks e concorrência
  - Simular carga de inserções/atualizações
  - Verificar deadlocks
- **Cuidados**: **PODE MODIFICAR DADOS** - use apenas em desenvolvimento/teste
- **Recomendação**: Use menos threads (2-10) para evitar deadlocks

### 📋 Queries Mistas (padrão)
- **Incluem**: Todos os tipos
- **Casos de uso**: Simular carga real mista
- **Recomendação**: Use threads moderadas (5-20)

### 💫 Filtro Avançado de Queries

O script possui um **sistema de filtragem inteligente** que automaticamente remove queries irrelevantes:

#### 🚫 Schemas de Sistema Filtrados
- **information_schema**: Metadados do banco de dados
- **performance_schema**: Métricas de performance do MySQL
- **sys**: Views e procedures do sistema MySQL
- **mysql**: Tabelas internas do MySQL (users, grants, etc)
- **heartbeat**: Monitoramento de replicação (rds_heartbeat*, heartbeat*)

#### ⚙️ Configurações Filtradas
- **SET SESSION**: Configurações de sessão
- **SET NAMES**: Configurações de charset
- **SHOW**: Comandos informativos
- **SELECT @@**: Variáveis do sistema

#### 🎯 Exemplos de Queries Filtradas

**❌ Queries de Metadados:**
```sql
SELECT * FROM information_schema.tables
SELECT * FROM performance_schema.events_waits_current
```

**❌ Queries de Heartbeat:**
```sql
SELECT value FROM mysql.rds_heartbeat2
SELECT count(*) WHERE TABLE_NAME = 'rds_heartbeat2'
```

**❌ Configurações:**
```sql
SET NAMES utf8mb4
SET SESSION sql_mode = 'STRICT_TRANS_TABLES'
```

#### 📈 Estatísticas de Filtro
```
📊 ESTATÍSTICAS DE EXTRAÇÃO
Total de queries processadas: 3.104
  • Queries de leitura (SELECT): 1.264
  • Queries de escrita (INSERT/UPDATE/DELETE): 449
  • Queries de sistema (filtradas): 1.093 ❌
  • Queries não classificadas: 288
  • Queries ignoradas (SET, etc): 10 ❌

Queries extraídas: 2.001 (64% são de aplicação úteis)
```

#### 💪 Benefícios do Filtro
- ✅ **Testes realistas**: Apenas queries que impactam usuários finais
- ✅ **Performance otimizada**: Sem queries lentas de metadados
- ✅ **Resultados precisos**: Métricas baseadas em carga real
- ✅ **Diagnóstico facilitado**: Foco em problemas reais de aplicação
- ✅ **Comparações confiáveis**: Testes consistentes entre execuções

## 📈 Interpretação dos Resultados

O relatório gerado incluirá:

### Resumo Geral
- **Duração total**: Tempo total do teste
- **Threads utilizadas**: Número de conexões concorrentes
- **Taxa de sucesso**: Percentual de queries bem-sucedidas

### Estatísticas de Performance
- **Queries por segundo**: Throughput geral do sistema
- **Tempo médio de resposta**: Latência média
- **Tempo mínimo/máximo**: Faixa de latências observadas

### Detalhes por Thread
- Performance individual de cada thread
- Identificação de threads com problemas

### Análise de Erros
- Lista de erros encontrados
- Classificação por tipo de erro

## 🔍 Monitoramento

Durante a execução, monitore:

1. **Log em tempo real:**
```bash
tail -f stress_test.log
```

2. **Performance do MySQL:**
```sql
SHOW PROCESSLIST;
SHOW ENGINE INNODB STATUS;
```

3. **Recursos do sistema:**
```bash
top -p $(pgrep mysql)
iostat -x 1
```

## ⚠️ Considerações Importantes

### Antes de Executar
1. **Backup**: Sempre faça backup do banco antes de testes intensos
2. **Ambiente**: Execute preferencialmente em ambiente de desenvolvimento/teste
3. **Recursos**: Monitore CPU, memória e I/O durante o teste
4. **Conexões**: Verifique o limite de conexões do MySQL (`max_connections`)

### Durante o Teste
- O teste pode impactar significativamente a performance do banco
- Monitore logs de erro do MySQL
- Interrompa com `Ctrl+C` se necessário

### Após o Teste
- Revise o relatório gerado
- Analise logs para identificar gargalos
- Compare resultados entre diferentes configurações

## 📝 Arquivos Gerados

- `stress_test.log`: Log detalhado da execução
- `stress_test_report_YYYYMMDD_HHMMSS.txt`: Relatório de resultados
- `queries.sql`: Queries extraídas do log (se aplicável)

## 🐛 Troubleshooting

### Erro de Conexão
```
Erro ao conectar no MySQL: (2003, "Can't connect to MySQL server")
```
**Solução:** Verifique host, porta, usuário e senha no `.env`

### Timeout de Query
```
Query failed after 3 attempts: (1205, 'Lock wait timeout exceeded')
```
**Solução:** Aumente `QUERY_TIMEOUT` no `.env` ou reduza número de threads

### Memória Insuficiente
```
MemoryError ou sistema lento
```
**Solução:** Reduza número de threads ou aumente `MAX_RETRIES`

### Nenhuma Query Extraída
```
Total de queries extraídas: 0
```
**Solução:** Verifique formato do arquivo de log ou ajuste padrões no `extract_queries.py`

## 🎯 Casos de Uso Reais

### 📈 Otimização de Performance
```bash
# Teste apenas queries de leitura para otimizar índices
python extract_queries.py general.log -o read_queries.sql -t read -m 5000
python mysql_stress_test.py -t 20 -d 120 -f read_queries.sql
```

### 🔒 Teste de Concorrência
```bash
# Teste queries de escrita para identificar deadlocks
python extract_queries.py general.log -o write_queries.sql -t write -m 1000  
python mysql_stress_test.py -t 8 -d 60 -f write_queries.sql
```

### 📊 Benchmark de Hardware
```bash
# Teste escalonamento com diferentes números de threads
for threads in 5 10 20 50; do
  python mysql_stress_test.py -t $threads -d 60
  sleep 30
done
```

### 🐛 Debug de Problemas
```bash
# Análise do que será filtrado antes do teste
python teste_filtro_sistema.py general.log

# Teste focado em queries problemáticas
python mysql_stress_test.py -t 5 -q 100 # Poucas queries para debug
```

## 🤝 Suporte

Para problemas ou melhorias:
1. Verifique os logs detalhados
2. Teste com configurações mais conservadoras
3. Monitore recursos do sistema
4. Analise logs do MySQL para erros específicos# mysql-stress-test-genlog
