#!python
#-*- coding: utf-8 -*-

"""
Extrator de Queries SQL do MySQL/MariaDB General Log
Suporta MySQL 5.7+, MySQL 8.0+ e MariaDB 10.11+

Autor: Jaci Turazzi
Versão: 2.0 - Suporte para MariaDB 10.11
"""

import argparse
import re
import os
from datetime import datetime
from collections import defaultdict

# Carrega variáveis de ambiente se arquivo .env existir
try:
    from dotenv import load_dotenv
    if os.path.exists('.env'):
        load_dotenv()
except ImportError:
    pass

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = ""
    class Style:
        BRIGHT = RESET_ALL = ""

def print_colored(text, color=None):
    """Imprime texto colorido se colorama estiver disponível"""
    if COLORS_AVAILABLE and color:
        print(f"{color}{text}{Style.RESET_ALL}")
    else:
        print(text)

def detect_log_format(log_file):
    """
    Detecta automaticamente o formato do log (MySQL ou MariaDB)
    
    Returns:
        str: 'mysql' ou 'mariadb'
    """
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if i > 20:  # Verifica apenas as primeiras 20 linhas
                break
            
            line = line.strip()
            
            # Formato MariaDB 10.11: YYMMDD HH:MM:SS
            if re.match(r'^\d{6}\s+\d{2}:\d{2}:\d{2}\s+\d+\s+Query', line):
                return 'mariadb'
            
            # Formato MySQL 8.0+: ISO timestamp
            if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s+\d+\s+Query', line):
                return 'mysql'
            
            # Formato MySQL 5.7: Simplified timestamp
            if re.match(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+\d+\s+Query', line):
                return 'mysql'
    
    # Default para MySQL se não conseguir detectar
    return 'mysql'

def get_patterns_for_format(log_format):
    """
    Retorna os padrões regex apropriados para o formato do log
    
    Args:
        log_format (str): 'mysql' ou 'mariadb'
        
    Returns:
        tuple: (query_pattern, connect_pattern, skip_header_lines)
    """
    if log_format == 'mariadb':
        # MariaDB 10.11 formato: 251027 16:37:19     3 Query    INSERT...
        query_pattern = re.compile(r'^(\d{6}\s+\d{2}:\d{2}:\d{2})\s+(\d+)\s+Query\s+(.+)$')
        connect_pattern = re.compile(r'^(\d{6}\s+\d{2}:\d{2}:\d{2})\s+(\d+)\s+(Connect|Quit)', re.IGNORECASE)
        skip_lines = 3  # Pula cabeçalho do MariaDB
        
    else:  # MySQL
        # MySQL 8.0+ formato: 2024-10-27T16:30:45.123456Z    123 Query    SELECT...
        query_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+(\d+)\s+Query\s+(.+)$')
        connect_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+(\d+)\s+(Connect|Quit)', re.IGNORECASE)
        skip_lines = 0  # MySQL não tem cabeçalho fixo
    
    return query_pattern, connect_pattern, skip_lines

def is_system_query(query):
    """Verifica se é uma query de sistema (information_schema, performance_schema, etc)"""
    system_patterns = [
        r'information_schema',
        r'performance_schema', 
        r'mysql\.',
        r'sys\.',
    ]
    
    query_lower = query.lower()
    return any(re.search(pattern, query_lower) for pattern in system_patterns)

def should_ignore_query(query, ignore_patterns):
    """Verifica se a query deve ser ignorada"""
    query_stripped = query.strip()
    if not query_stripped:
        return True
    
    return any(pattern.search(query_stripped) for pattern in ignore_patterns)

def get_query_type(query):
    """Classifica o tipo da query"""
    query_upper = query.strip().upper()
    
    if query_upper.startswith(('SELECT', 'SHOW', 'DESC', 'DESCRIBE', 'EXPLAIN')):
        return 'read'
    elif query_upper.startswith(('INSERT', 'UPDATE', 'DELETE', 'REPLACE', 'TRUNCATE')):
        return 'write'
    elif query_upper.startswith(('CREATE', 'DROP', 'ALTER', 'RENAME')):
        return 'ddl'
    else:
        return 'unknown'

def clean_query(query):
    """
    Limpa e formata a query para melhor legibilidade
    """
    # Remove quebras de linha desnecessárias e espaços extras
    cleaned = re.sub(r'\s+', ' ', query.strip())
    
    # Se a query for muito longa, quebra em linhas lógicas
    if len(cleaned) > 200:
        # Quebra após vírgulas em listas de valores
        cleaned = re.sub(r',\s*', ',\n    ', cleaned)
        # Quebra após palavras-chave principais
        cleaned = re.sub(r'\b(FROM|WHERE|JOIN|ORDER BY|GROUP BY|HAVING|LIMIT)\b', r'\n\1', cleaned, flags=re.IGNORECASE)
    
    return cleaned

def extract_queries(log_file, output_file, max_queries=None, query_type=None):
    """
    Extrai queries SQL válidas do arquivo de log do MySQL/MariaDB
    
    Args:
        log_file: Arquivo de log do MySQL/MariaDB
        output_file: Arquivo de saída
        max_queries: Número máximo de queries para extrair
        query_type: Tipo de queries ('read', 'write', 'ddl' ou None para todas)
    """
    queries = []
    current_query = ""
    in_query = False
    query_count = 0
    query_stats = defaultdict(int)
    
    # Detecta automaticamente o formato do log
    log_format = detect_log_format(log_file)
    print_colored(f"📊 Formato detectado: {log_format.upper()}", Fore.CYAN)
    
    # Obtém padrões apropriados para o formato
    query_pattern, connect_pattern, skip_lines = get_patterns_for_format(log_format)
    
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
        r'USE `',
        r'SET SQL_SAFE_UPDATES',
        r'SET time_zone',
    ]
    ignore_compiled = [re.compile(pattern, re.IGNORECASE) for pattern in ignore_patterns]
    
    print_colored(f"Processando arquivo: {log_file}", Fore.YELLOW)
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                # Pula linhas de cabeçalho conforme o formato
                if line_num <= skip_lines:
                    continue
                    
                if line_num % 100000 == 0:
                    print_colored(f"Processadas {line_num:,} linhas, {len(queries):,} queries extraídas", Fore.BLUE)
                
                line = line.strip()
                if not line:
                    continue
                
                # Verifica se é uma linha de conexão/quit
                if connect_pattern.match(line):
                    if in_query and current_query.strip():
                        # Finaliza query anterior se existir
                        query = clean_query(current_query)
                        
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
                match = query_pattern.match(line)
                if match:
                    # Salva query anterior se existir
                    if in_query and current_query.strip():
                        query = clean_query(current_query)
                        
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
                    timestamp, connection_id, query_text = match.groups()
                    if not should_ignore_query(query_text, ignore_compiled):
                        current_query = query_text
                        in_query = True
                    else:
                        query_stats['ignored'] += 1
                        current_query = ""
                        in_query = False
                        
                elif in_query:
                    # Linha de continuação da query
                    # Para MariaDB: linhas sem timestamp são continuações
                    # Para MySQL: também verifica se não é uma nova linha com timestamp
                    is_continuation = True
                    
                    if log_format == 'mariadb':
                        # No MariaDB, se não começa com timestamp, é continuação
                        is_continuation = not re.match(r'^\d{6}\s+\d{2}:\d{2}:\d{2}', line)
                    else:
                        # No MySQL, se não começa com timestamp ISO, é continuação
                        is_continuation = not re.match(r'^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}', line)
                    
                    if is_continuation:
                        current_query += "\n" + line
        
        # Processa última query se existir
        if in_query and current_query.strip():
            query = clean_query(current_query)
            if is_system_query(query):
                query_stats['system'] += 1
            elif not should_ignore_query(query, ignore_compiled):
                q_type = get_query_type(query)
                query_stats[q_type] += 1
                if query_type is None or q_type == query_type:
                    queries.append(query)
            else:
                query_stats['ignored'] += 1
    
    except FileNotFoundError:
        print_colored(f"❌ Erro: Arquivo {log_file} não encontrado!", Fore.RED)
        return
    except PermissionError:
        print_colored(f"❌ Erro: Sem permissão para ler o arquivo {log_file}!", Fore.RED)
        return
    except Exception as e:
        print_colored(f"❌ Erro inesperado: {e}", Fore.RED)
        return
    
    # Salva queries no arquivo de saída
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"-- Queries extraídas do {log_format.upper()} General Log\n")
            f.write(f"-- Arquivo fonte: {log_file}\n")
            f.write(f"-- Filtro aplicado: {query_type if query_type else 'Nenhum'}\n")
            f.write(f"-- Total extraído: {len(queries)} queries\n")
            f.write(f"-- Data de extração: {datetime.now()}\n")
            f.write("--\n")
            f.write("-- ESTATÍSTICAS:\n")
            f.write(f"--   Leitura: {query_stats['read']}\n")
            f.write(f"--   Escrita: {query_stats['write']}\n")
            f.write(f"--   DDL: {query_stats['ddl']}\n")
            f.write(f"--   Sistema: {query_stats['system']}\n")
            f.write(f"--   Não classificadas: {query_stats['unknown']}\n")
            f.write(f"--   Ignoradas: {query_stats['ignored']}\n")
            f.write("\n\n")
            
            for i, query in enumerate(queries, 1):
                f.write(f"-- Query {i}\n")
                f.write(f"{query};\n\n")
    
    except PermissionError:
        print_colored(f"❌ Erro: Sem permissão para escrever no arquivo {output_file}!", Fore.RED)
        return
    
    # Estatísticas finais
    total_processed = sum(query_stats.values())
    
    print_colored("\n📊 ESTATÍSTICAS DE EXTRAÇÃO", Fore.GREEN)
    print(f"Total de queries processadas: {total_processed:,}")
    print_colored(f"  • Queries de leitura (SELECT): {query_stats['read']:,}", Fore.CYAN)
    print_colored(f"  • Queries de escrita (INSERT/UPDATE/DELETE): {query_stats['write']:,}", Fore.YELLOW)
    print_colored(f"  • Queries DDL (CREATE/DROP/ALTER): {query_stats['ddl']:,}", Fore.MAGENTA)
    print_colored(f"  • Queries de sistema (information_schema, etc): {query_stats['system']:,}", Fore.BLUE)
    print_colored(f"  • Queries não classificadas: {query_stats['unknown']:,}", Fore.WHITE)
    print_colored(f"  • Queries ignoradas (SET, etc): {query_stats['ignored']:,}", Fore.RED)
    print()
    print(f"Queries extraídas para o arquivo: {len(queries):,}")
    print()
    print_colored(f"✅ Queries salvas em: {output_file}", Fore.GREEN)

def main():
    parser = argparse.ArgumentParser(
        description='Extrai queries SQL do general log do MySQL/MariaDB',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python extract_queries.py /var/log/mysql/general.log -o queries.sql
  python extract_queries.py mysql.log -o select_queries.sql -t read -m 1000
  python extract_queries.py mariadb.log -o insert_queries.sql -t write
        """
    )
    
    parser.add_argument('log_file', help='Arquivo de log do MySQL/MariaDB')
    parser.add_argument('-o', '--output', default='queries.sql', 
                       help='Arquivo de saída (padrão: queries.sql)')
    parser.add_argument('-m', '--max-queries', type=int, 
                       help='Número máximo de queries para extrair')
    parser.add_argument('-t', '--type', choices=['read', 'write', 'ddl'], 
                       help='Tipo de queries a extrair (read=SELECT, write=INSERT/UPDATE/DELETE, ddl=CREATE/DROP/ALTER)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.log_file):
        print_colored(f"❌ Erro: Arquivo {args.log_file} não encontrado!", Fore.RED)
        return 1
    
    extract_queries(args.log_file, args.output, args.max_queries, args.type)
    return 0

if __name__ == '__main__':
    exit(main())