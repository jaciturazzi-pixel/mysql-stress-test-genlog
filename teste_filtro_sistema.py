#!python
"""
Script de teste para demonstrar a efetividade do filtro de queries de sistema
Compara estatísticas antes e depois da implementação do filtro
"""
import re
import sys
from extract_queries import is_system_query, get_query_type, should_ignore_query

def analyze_log_sample(log_file, max_lines=5000):
    """
    Analisa uma amostra do log para mostrar estatísticas
    """
    queries_found = []
    stats = {
        'total_lines': 0,
        'query_lines': 0,
        'system_queries': 0,
        'app_queries': 0,
        'read_queries': 0,
        'write_queries': 0,
        'ignored_queries': 0
    }
    
    # Padrões para identificar queries
    query_start_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s+\d+\s+Query\s+(.+)')
    ignore_patterns = [
        re.compile(r'SET SESSION sql_mode', re.IGNORECASE),
        re.compile(r'SET NAMES', re.IGNORECASE),
        re.compile(r'SET @@', re.IGNORECASE),
    ]
    
    current_query = ""
    in_query = False
    
    print("🔍 Analisando amostra do log...")
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            stats['total_lines'] += 1
            if line_num > max_lines:
                break
                
            line = line.strip()
            if not line:
                continue
                
            # Verifica se é início de uma nova query
            match = query_start_pattern.match(line)
            if match:
                # Processa query anterior se existir
                if in_query and current_query.strip():
                    process_query(current_query.strip(), stats, ignore_patterns)
                
                # Inicia nova query
                current_query = match.group(1)
                in_query = True
                stats['query_lines'] += 1
            elif in_query:
                # Linha de continuação
                current_query += "\n" + line
        
        # Processa última query
        if in_query and current_query.strip():
            process_query(current_query.strip(), stats, ignore_patterns)
    
    print(f"✅ Análise concluída ({stats['total_lines']} linhas processadas)")
    return stats

def process_query(query, stats, ignore_patterns):
    """
    Processa uma query individual e atualiza estatísticas
    """
    if should_ignore_query(query, ignore_patterns):
        stats['ignored_queries'] += 1
        return
    
    if is_system_query(query):
        stats['system_queries'] += 1
    else:
        stats['app_queries'] += 1
        query_type = get_query_type(query)
        if query_type == 'read':
            stats['read_queries'] += 1
        elif query_type == 'write':
            stats['write_queries'] += 1

def print_comparison_report(stats):
    """
    Exibe relatório comparativo
    """
    total_queries = stats['system_queries'] + stats['app_queries'] + stats['ignored_queries']
    
    print(f"""
🎯 RELATÓRIO DE ANÁLISE DO FILTRO DE SISTEMA

📊 ESTATÍSTICAS GERAIS:
  • Total de linhas processadas: {stats['total_lines']:,}
  • Linhas de query identificadas: {stats['query_lines']:,}
  • Queries processadas: {total_queries:,}

🔍 CLASSIFICAÇÃO DAS QUERIES:
  • Queries de aplicação (úteis): {stats['app_queries']:,} ({stats['app_queries']/total_queries*100:.1f}%)
  • Queries de sistema (filtradas): {stats['system_queries']:,} ({stats['system_queries']/total_queries*100:.1f}%)
  • Queries ignoradas (SET, etc): {stats['ignored_queries']:,} ({stats['ignored_queries']/total_queries*100:.1f}%)

📈 DETALHAMENTO DE QUERIES DE APLICAÇÃO:
  • Queries de leitura (SELECT): {stats['read_queries']:,}
  • Queries de escrita (INSERT/UPDATE/DELETE): {stats['write_queries']:,}
  • Outras queries de aplicação: {stats['app_queries'] - stats['read_queries'] - stats['write_queries']:,}

💡 BENEFÍCIOS DO FILTRO:
  • Redução de queries irrelevantes: {stats['system_queries']:,} queries filtradas
  • Foco em queries reais: {stats['app_queries']/total_queries*100:.1f}% das queries são de aplicação
  • Melhoria na qualidade do teste: Apenas queries que impactam usuários finais

⚠️  QUERIES DE SISTEMA MAIS COMUNS FILTRADAS:
  • SELECT ... FROM information_schema.*
  • SELECT ... FROM performance_schema.*
  • SELECT ... FROM sys.*
  • SELECT ... FROM mysql.*
  • SELECT ... FROM heartbeat.*
""")

def main():
    if len(sys.argv) != 2:
        print("Uso: python3 teste_filtro_sistema.py <arquivo_log_mysql>")
        print("Exemplo: python3 teste_filtro_sistema.py ../general_all.log")
        sys.exit(1)
    
    log_file = sys.argv[1]
    
    try:
        stats = analyze_log_sample(log_file, max_lines=10000)
        print_comparison_report(stats)
        
        print("\n🚀 PRÓXIMOS PASSOS:")
        print("  1. Execute: python3 extract_queries.py {} -o queries_clean.sql -m 2000".format(log_file))
        print("  2. Compare com extração sem filtro para ver a diferença")
        print("  3. Use as queries filtradas para testes mais realistas")
        
    except FileNotFoundError:
        print(f"❌ Erro: Arquivo '{log_file}' não encontrado")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()