#!python
"""
Script para extrair queries SQL válidas do arquivo de log general do MySQL
Remove queries de configuração (SET, CONNECT, etc.) e preserva apenas as queries de consulta/modificação
"""
import re
import argparse
import sys


def extract_queries(log_file, output_file, max_queries=None, query_type=None):
    """
    Extrai queries SQL válidas do arquivo de log
    
    Args:
        log_file: Arquivo de log do MySQL
        output_file: Arquivo de saída
        max_queries: Número máximo de queries para extrair
        query_type: Tipo de queries ('read', 'write' ou None para todas)
    """
    queries = []
    current_query = ""
    in_query = False
    query_count = 0
    query_stats = {'read': 0, 'write': 0, 'unknown': 0, 'ignored': 0, 'system': 0}
    
    # Padrões para identificar início de queries e linhas a ignorar
    query_start_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s+\d+\s+Query\s+(.+)')
    ignore_patterns = [
        r'SET SESSION sql_mode',
        r'SET NAMES',
        r'SET @@',
        r'SET sql_mode',
        r'SHOW',
        r'SELECT @@',
        r'SET character_set',
        r'SET FOREIGN_KEY_CHECKS',
        r'SET UNIQUE_CHECKS',
        r'SET AUTOCOMMIT',
        r'START TRANSACTION',
        r'COMMIT',
        r'ROLLBACK',
    ]
    ignore_compiled = [re.compile(pattern, re.IGNORECASE) for pattern in ignore_patterns]
    
    connect_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s+\d+\s+(Connect|Quit)', re.IGNORECASE)
    continuation_pattern = re.compile(r'^\s+(.+)')
    
    print(f"Processando arquivo: {log_file}")
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            if line_num % 100000 == 0:
                print(f"Processadas {line_num} linhas, {len(queries)} queries extraídas")
            
            line = line.strip()
            if not line:
                continue
                
            # Verifica se é uma linha de conexão/quit
            if connect_pattern.match(line):
                if in_query and current_query.strip():
                    # Finaliza query anterior se existir
                    query = current_query.strip()
                    
                    # Verifica se é query de sistema primeiro
                    if is_system_query(query):
                        query_stats['system'] += 1
                    elif not should_ignore_query(query, ignore_compiled):
                        q_type = get_query_type(query)
                        query_stats[q_type] += 1
                        
                        # Aplica filtro de tipo se especificado
                        if query_type is None or q_type == query_type:
                            queries.append(query)
                            query_count += 1
                            if max_queries and query_count >= max_queries:
                                break
                    else:
                        query_stats['ignored'] += 1
                current_query = ""
                in_query = False
                continue
            
            # Verifica se é início de uma nova query
            match = query_start_pattern.match(line)
            if match:
                # Salva query anterior se existir
                if in_query and current_query.strip():
                    query = current_query.strip()
                    
                    # Verifica se é query de sistema primeiro
                    if is_system_query(query):
                        query_stats['system'] += 1
                    elif not should_ignore_query(query, ignore_compiled):
                        q_type = get_query_type(query)
                        query_stats[q_type] += 1
                        
                        # Aplica filtro de tipo se especificado
                        if query_type is None or q_type == query_type:
                            queries.append(query)
                            query_count += 1
                            if max_queries and query_count >= max_queries:
                                break
                    else:
                        query_stats['ignored'] += 1
                
                # Inicia nova query
                query_text = match.group(1)
                if not should_ignore_query(query_text, ignore_compiled):
                    current_query = query_text
                    in_query = True
                else:
                    current_query = ""
                    in_query = False
            elif in_query:
                # Linha de continuação da query
                cont_match = continuation_pattern.match(line)
                if cont_match:
                    current_query += "\n" + cont_match.group(1)
                else:
                    # Linha sem numeração, provavelmente continuação
                    current_query += "\n" + line
    
    # Processa última query se existir
    if in_query and current_query.strip():
        query = current_query.strip()
        
        # Verifica se é query de sistema primeiro
        if is_system_query(query):
            query_stats['system'] += 1
        elif not should_ignore_query(query, ignore_compiled):
            q_type = get_query_type(query)
            query_stats[q_type] += 1
            
            # Aplica filtro de tipo se especificado
            if query_type is None or q_type == query_type:
                queries.append(query)
                query_count += 1
        else:
            query_stats['ignored'] += 1
    
    # Exibe estatísticas detalhadas
    total_processed = sum(query_stats.values())
    filter_msg = f" (filtro: {query_type})" if query_type else ""
    
    print(f"\n📊 ESTATÍSTICAS DE EXTRAÇÃO{filter_msg}")
    print(f"Total de queries processadas: {total_processed}")
    print(f"  • Queries de leitura (SELECT): {query_stats['read']}")
    print(f"  • Queries de escrita (INSERT/UPDATE/DELETE): {query_stats['write']}")
    print(f"  • Queries de sistema (information_schema, etc): {query_stats['system']}")
    print(f"  • Queries não classificadas: {query_stats['unknown']}")
    print(f"  • Queries ignoradas (SET, etc): {query_stats['ignored']}")
    print(f"\nQueries extraídas para o arquivo: {len(queries)}")
    
    # Salva queries no arquivo de saída
    with open(output_file, 'w', encoding='utf-8') as f:
        # Adiciona cabeçalho com estatísticas
        f.write(f"-- Queries extraídas do MySQL General Log\n")
        f.write(f"-- Arquivo fonte: {log_file}\n")
        f.write(f"-- Filtro aplicado: {query_type or 'Nenhum'}\n")
        f.write(f"-- Total extraído: {len(queries)} queries\n")
        f.write(f"-- Data de extração: {__import__('datetime').datetime.now()}\n")
        f.write(f"--\n")
        f.write(f"-- ESTATÍSTICAS:\n")
        f.write(f"--   Leitura: {query_stats['read']}\n")
        f.write(f"--   Escrita: {query_stats['write']}\n")
        f.write(f"--   Sistema: {query_stats['system']}\n")
        f.write(f"--   Não classificadas: {query_stats['unknown']}\n")
        f.write(f"--   Ignoradas: {query_stats['ignored']}\n")
        f.write(f"\n")
        
        for i, query in enumerate(queries):
            query_type_comment = get_query_type(query).upper()
            f.write(f"-- Query {i+1} ({query_type_comment})\n")
            f.write(query + "\n")
            f.write(";\n\n")
    
    print(f"\n✅ Queries salvas em: {output_file}")
    return len(queries)


def get_query_type(query):
    """
    Determina o tipo da query (read ou write)
    
    Args:
        query: Query SQL para classificar
        
    Returns:
        'read' para queries de leitura, 'write' para queries de escrita
    """
    query_upper = query.upper().strip()
    
    # Queries de leitura
    read_keywords = ['SELECT', 'SHOW', 'DESCRIBE', 'DESC', 'EXPLAIN', 'ANALYZE']
    
    # Queries de escrita
    write_keywords = ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 
                     'TRUNCATE', 'REPLACE', 'MERGE', 'UPSERT']
    
    # Verifica primeiro token significativo
    tokens = query_upper.split()
    if not tokens:
        return 'unknown'
        
    first_token = tokens[0]
    
    if first_token in read_keywords:
        return 'read'
    elif first_token in write_keywords:
        return 'write'
    else:
        return 'unknown'


def is_system_query(query):
    """
    Verifica se a query é uma consulta de sistema (schemas internos do MySQL)
    
    Args:
        query: Query SQL para verificar
        
    Returns:
        True se for query de sistema, False caso contrário
    """
    query_upper = query.upper().strip()
    
    # Schemas de sistema do MySQL
    system_schemas = [
        'INFORMATION_SCHEMA',
        'PERFORMANCE_SCHEMA', 
        'SYS',
        'MYSQL',
        'HEARTBEAT'
    ]
    
    # Padrões que indicam queries de sistema
    system_patterns = [
        r'\bINFORMATION_SCHEMA\b',
        r'\bPERFORMANCE_SCHEMA\b',
        r'\bSYS\b\.',  # sys.table_name
        r'\bMYSQL\b\.',  # mysql.user, etc
        r'\bHEARTBEAT\b\.',  # heartbeat.table_name
        r'\bRDS_HEARTBEAT\w*\b',  # rds_heartbeat, rds_heartbeat2, etc
        r'\bHEARTBEAT\w*\b',  # heartbeat tables
        r'FROM\s+SYS\b',
        r'JOIN\s+SYS\b',
        r'FROM\s+MYSQL\b',
        r'JOIN\s+MYSQL\b',
        r'FROM\s+HEARTBEAT\b',
        r'JOIN\s+HEARTBEAT\b'
    ]
    
    # Verifica se menciona schemas de sistema
    for schema in system_schemas:
        if schema in query_upper:
            return True
    
    # Verifica padrões mais específicos
    import re
    for pattern in system_patterns:
        if re.search(pattern, query_upper, re.IGNORECASE):
            return True
            
    return False


def should_ignore_query(query, ignore_patterns):
    """
    Verifica se a query deve ser ignorada (padrões como SET, SHOW, etc)
    Nota: Não verifica queries de sistema aqui, isso é feito separadamente
    """
    query_upper = query.upper().strip()
    
    # Ignora queries vazias ou muito pequenas
    if len(query_upper) < 10:
        return True
    
    # Verifica padrões a ignorar
    for pattern in ignore_patterns:
        if pattern.search(query):
            return True
    
    return False


def main():
    parser = argparse.ArgumentParser(description='Extrai queries SQL do log general do MySQL')
    parser.add_argument('log_file', help='Arquivo de log do MySQL')
    parser.add_argument('-o', '--output', default='queries.sql', help='Arquivo de saída (default: queries.sql)')
    parser.add_argument('-m', '--max-queries', type=int, help='Número máximo de queries a extrair')
    parser.add_argument('-t', '--type', choices=['read', 'write'], 
                       help='Filtrar por tipo de query (read=SELECT, write=INSERT/UPDATE/DELETE)')
    
    args = parser.parse_args()
    
    try:
        extract_queries(args.log_file, args.output, args.max_queries, args.type)
    except FileNotFoundError:
        print(f"Erro: Arquivo '{args.log_file}' não encontrado")
        sys.exit(1)
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()